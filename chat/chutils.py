from companies_house.api import CompaniesHouseAPI
from datetime import datetime
from string import capwords
import pprint


api_key = 'gHggW0wcFUkPigIifYRo864nCxGBqqIYMLm3Pd_O'
ch = CompaniesHouseAPI(api_key)

company_request_cache = {}
officers_request_cache = {} 



def get_officers(company_number):

    officers_request = None

    if company_number in officers_request_cache is True:
        officers_request = officers_request_cache[company_number]
    else:
        company_request = get_company(company_number)

        if company_request is not None:          
            officers_request = ch.list_company_officers(company_number=company_number) 

            if officers_request is not None:
                ps = datetime.fromisoformat( company_request['accounts']['next_accounts']['period_start_on'] )
                pe = datetime.fromisoformat( company_request['accounts']['next_accounts']['period_end_on'] )

                officers_request.update(  {
                    'period_start_datetime' : ps,
                    'period_end_datetime' : pe,
                } )

                for officer in officers_request['items'] :                
                    
                    ad = datetime.fromisoformat( officer['appointed_on'] )
                    rd = datetime.fromisoformat( officer['resigned_on'] ) if 'resigned_on' in officer else None

                    # add a number of officer information properties to the officer item.
                    officer.update( _get_officer_appointment_info(ps, pe, ad, rd) )
                    officer.update( _get_officer_role_info( officer['officer_role'] ) )
                    officer.update( _get_officer_name_info( officer['name'], officer['is_person'] ) )
                    officer.update( _get_officer_misc_info( officer ) )

                # sort officers by appointment date (descending)
                officers_request['items'] = sorted(officers_request['items'],key=lambda k: k['appointed_on_datetime'], reverse=True)

                # count officers 
                officers_request['count'] = _get_officer_count_info( officers_request['items'] )

        officers_request_cache[company_number] = officers_request

    return officers_request



def _get_officer_appointment_info(ps: datetime, pe: datetime, ad: datetime, rd: datetime):

    # calculate whether its a current, previous or future director, relative to current period.
    if rd is not None and rd < ps:
        appointment_status = "previous"
    elif ad <= pe and ( rd is None or rd >= ps ) :
        appointment_status = "current"
    else:
        appointment_status = "future"

    appointment_info = {
        'appointed_on_datetime' : ad,
        'resigned_on_datetime' : rd,
        'is_current' : True if appointment_status is "current" else False,
        'is_previous' : True if appointment_status is "previous" else False,
        'is_future': True if appointment_status is "future" else False,
        'appointment_status' : appointment_status,
    }

    appointment_info.update( _get_officer_appointment_info_disclosures( ps, pe, ad, rd ) )

    return appointment_info


def _get_officer_appointment_info_disclosures( ps:datetime, pe:datetime, ad:datetime, rd:datetime ):
    
    # set disclosure default texts (not condition on whether they have arisen on or after current period)
    ad_short = _datetime_to_str_short(ad)
    ad_long = _datetime_to_str_long(ad)

    rd_short = "" if rd is None else _datetime_to_str_short(rd)
    rd_long =  "" if rd is None else _datetime_to_str_long(rd)

    info_long = "(appointed on " + ad_long + ( ")" if rd is None else ", resigned on " + rd_long + ")")

    # set disclosure "current" texts (included conditionally on whether they have arisen on or after current period)
    if ad >= ps :
        disclosure =  "(appointed on " + ad_long + ( ")" if rd is None else ", resigned on " + rd_long + ")")
    elif rd is not None and rd >= ps:
        disclosure  = "(resigned " + rd_long + ")"
    else:
        disclosure  = ""

    return {
        'appointment_period_disclosure' : disclosure
    }



def _get_officer_role_info( officer_role: str ):
    role_info = {
        'is_corporate_entity' : True if officer_role.find('corporate') >= 0 else False,
        'is_person' :  False if officer_role.find('corporate') >= 0 else True,
        'is_secretary' : True if officer_role.find('secretary') >= 0 else False,
        'is_director' : True if officer_role.find('director') >= 0 else False
        }

    if(role_info['is_director'] is True ):
        role_info['officer_position'] = "director"
        role_info['is_other'] = False
    elif(role_info['is_secretary'] is True ):
        role_info['officer_position'] = "secretary"
        role_info['is_other'] = False
    else:
        role_info['officer_position'] = "other"
        role_info['is_other'] = True

    return role_info



def _get_officer_name_info( officer_name: str, officer_is_person: bool ):
    
    if( officer_is_person is True ):
        # extract forenames and surname from "names" - this is required because CH API doesn't return these properties.
        surname, part, forenames = officer_name.rpartition(', ')

        dn_full = capwords(forenames + ' ' + surname).strip()
        forename_initials = "".join( [w[0] for w in forenames.split() if w] ).upper()
        dn_initialled = (forename_initials + ' ' + capwords(surname) ).strip()

        return {
            'name_disclosure' : dn_full,
            'name_disclosure_initialled' : dn_initialled,
            'forenames': forenames,
            'surname' : surname
        }
    
    return {
        'name_disclosure' : officer_name,
        'name_disclosure_initialled' : officer_name
    }


def _get_officer_misc_info( officer : list ):

    misc_info = {
        'disclosure_nationality': '' if 'nationality' not in officer else officer['nationality'],
        'disclosure_occupation': '' if 'occupation' not in officer else officer['occupation'] 
    }

    misc_info.update( _get_officer_dob_info(officer) )

    return misc_info


def _get_officer_dob_info( officer : list ):

    if 'date_of_birth' in officer:
        
        try:
            day = officer['date_of_birth']['day']
        except KeyError:
            day = 1

        dt = datetime(
            int(officer['date_of_birth']['year']),
            int(officer['date_of_birth']['month']),
            int(day) )

        return {
            'date_of_birth_datetime' : dt
        }

    return {}


def _get_officer_count_info( officers : list ):
    # initiate counters.
    count_info = {
        'officers' : {'all':0,'previous':0,'current':0,'future':0},
        'director' : {'all':0,'previous':0,'current':0,'future':0},
        'secretary' : {'all':0,'previous':0,'current':0,'future':0},
        'other' : {'all':0,'previous':0,'current':0,'future':0},
    }

    for officer in officers:
        op = officer['officer_position']
        a_status = officer['appointment_status']

        count_info['officers']['all'] += 1
        count_info[op]['all'] += 1

        count_info['officers'][a_status] += 1
        count_info[op][a_status] += 1

    return count_info
        

def _datetime_to_str_short( dt:datetime ):
     return dt.strftime("%d %b %Y")

def _datetime_to_str_long( dt:datetime ):
     return dt.strftime("%d %B %Y")

def _datetime_to_str_without_day_short( dt:datetime ):
     return dt.strftime("%b %Y")

def _datetime_to_str_without_day_long( dt:datetime ):
     return dt.strftime("%B %Y")
    

def get_company(company_number):
    cr = None

    # if the request has previously been made, retrieve from cache, else perform remote API request and cache that request for future retrieval.
    if company_number in company_request_cache is True:
        cr = company_request_cache[company_number] 

    else:
        cr = ch.get_company(company_number)

        _generate_company_request_datetimes( cr )

    return cr


def _generate_company_request_datetimes( cr:dict = None ):
    
    if cr is not None :      
        
        date_fields = [
            ['accounts','last_accounts','period_start_on'],
            ['accounts','last_accounts','period_end_on'],
            ['accounts','next_accounts','due_on'],
            ['accounts','next_accounts','period_start_on'],
            ['accounts','next_accounts','period_end_on'],
            ['accounts','annual_return','last_made_up_to'],
            ['accounts','annual_return','next_due'],
            ['accounts','annual_return','next_made_up_to'],
            ['confirmation_statement','last_made_up_to'],
            ['confirmation_statement','next_due'],
            ['confirmation_statement','next_made_up_to'],
            ['date_of_cessation'],
            ['date_of_creation'],
            ['last_full_members_list_date'],
        ]

        try:
            for i in range( len( cr['previous_company_names'] ) ):
                date_fields.append( ['previous_company_names',i,'ceased_on'])
                date_fields.append( ['previous_company_names',i,'effective_from']) 
        except KeyError: pass

        for df in date_fields:
            try:
                ln = len(df)

                if ln == 1:
                    cr[ df[0] + '_datetime'] = datetime.fromisoformat( cr[ df[0] ] )
                elif ln == 2:
                    cr[ df[0] ][ df[1] + '_datetime'] = datetime.fromisoformat( cr[ df[0] ][ df[1] ] )
                elif ln == 3:
                    cr[df[0]][df[1]][ df[2] + '_datetime'] = datetime.fromisoformat( cr[ df[0] ][ df[1] ][ df[2] ] )
                elif ln == 4:
                    cr[ df[0] ][ df[1] ][ df[2] ][ df[3] + '_datetime'] = datetime.fromisoformat( cr[ df[0] ][ df[1] ][ df[2] ][ df[3] ] )
            except KeyError: pass






