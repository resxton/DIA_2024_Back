from django.contrib import admin
from django.urls import path
from lr1_code import views

urlpatterns = [
    path('admin/', admin.site.urls),
	path('', views.getConfigurationElementsPage, name='configuration_elements'),
	path('plane_configuration_element/<int:id>/', views.getConfigurationElementPage, name='configuration_element'),
	path('plane_configuration/<int:id>/', views.getConfigurationPage, name='configuration')
]
