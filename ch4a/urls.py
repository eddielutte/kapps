from django.urls import path

from . import views

urlpatterns = [
    # ex: /chat/
    path('', views.index, name='index'),
    # ex: /chat/search/
    path('search/', views.search, name='search'),
    # ex: /chat/results/
    path('results/', views.results, name='results'),
    # ex: /chat/detail/12345/
    path('detail/<str:company_search_number>/', views.detail, name='detail'),

]
