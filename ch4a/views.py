from django.http import HttpResponse
from django.template import loader
from companies_house.api import CompaniesHouseAPI
import chat.chutils


def index(request):
    return search(request)

def search(request):
    template = loader.get_template('chat/index.html')
    context = {
        'message': "This is the CHAT app welcome page with the search bar.",
    }
    return HttpResponse(template.render(context, request))

def results(request):
    return HttpResponse("This is the results page.")

def detail(request, company_search_number: str="0"):
    company_request = chat.chutils.get_company(company_search_number)
    company_found = True if company_request is not None else False

    officers_request = chat.chutils.get_officers(company_search_number) if company_found is True else None
        
    context = {
        'company_search_number' : company_search_number,
        'company_found' : company_found,
        'company_request' : company_request,
        'officers_request' : officers_request
    }

    template = loader.get_template('chat/detail.html')

    return HttpResponse(template.render(context, request))





