from django.http import HttpResponse
from django.shortcuts import render
from datetime import date

# def hello(request): 
#     return render(request, 'index.html', { 'data' : {
#         'current_date': date.today(),
#         'list': ['python', 'django', 'html']
#     }})


def getStartPage(request):
    return render(request, 'start.html')

def getMainPage(request):
    return render(request, 'main.html')

def getDetailPage(request):
    return render(request, 'detail.html')

def getConfigurationPage(request):
    return render(request, 'configuration.html')