from django.contrib import admin
from django.urls import path, include
from lr1_code import views
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
	path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
	path('', include(router.urls)),
    path(r'plane_configuration_elements/', views.ConfigurationElementsView.as_view(), name='configuration_elements'),
	path(r'plane_configuration_element/add/', views.add_new_element, name='add_new_configuration_element'),
    path(r'plane_configuration_element/<int:pk>/', views.ConfigurationElementView.as_view(), name='configuration_element'), 
	   
	path(r'plane_configurations/', views.ConfigurationView.as_view(), name='all_configurations'),
    path(r'plane_configuration_element/<int:pk>/edit/', views.put, name='configuration_element_put'),	
	path(r'users/', views.UsersList.as_view(), name='users-list'),
	# path('', views.getConfigurationElementsPage, name='configuration_elements'),
	# path('plane_configuration_element/<int:id>/', views.getConfigurationElementPage, name='configuration_element'),
	# path('plane_configuration/<int:id>/', views.getConfigurationPage, name='configuration'),
	# path('delete_plane_configuration/<int:id>/', views.deleteConfiguration, name='delete_configuration'),
	# path('add_plane_configuration_element/<int:element_id>/', views.addConfigurationElement, name='add_element_to_configuration'),
]
