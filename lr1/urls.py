from django.contrib import admin
from django.urls import path
from lr1_code import views

urlpatterns = [
    path('admin/', admin.site.urls),
	path('', views.getConfigurationElementsPage, name='configuration_elements'),
	path('plane_configuration_element/<int:id>/', views.getConfigurationElementPage, name='configuration_element'),
	path('plane_configuration/<int:id>/', views.getConfigurationPage, name='configuration'),
	path('delete_plane_configuration/<int:id>/', views.deleteConfiguration, name='delete_configuration'),
	path('add_plane_configuration_element/<int:element_id>/', views.addConfigurationElement, name='add_element_to_configuration'),
]
