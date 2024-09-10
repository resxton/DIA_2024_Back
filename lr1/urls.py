from django.contrib import admin
from django.urls import path
from lr1_code import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('hello/', views.hello),
	path('', views.getHomePage),
	path('jet-longitude/', views.getLongitudeDetail)
]
