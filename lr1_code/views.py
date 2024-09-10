from django.http import HttpResponse
from django.shortcuts import render
from datetime import date

def hello(request): 
    return render(request, 'index.html', { 'data' : {
        'current_date': date.today(),
        'list': ['python', 'django', 'html']
    }})


def getHomePage(request):
    return render(request, 'home.html')

def getLongitudeDetail(request):
    return render(request, 'longitude-detail.html')