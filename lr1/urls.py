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
    path(r'plane_configuration_element/<int:pk>/', views.ConfigurationElementView.as_view(), name='configuration_element'), 
	path(r'plane_configuration_element/<int:pk>/edit/', views.ConfigurationElementEditingView.as_view(), name='configuration_element'), 

	path(r'plane_configuration/<int:pk>/', views.ConfigurationDetailView.as_view(), name='detail_configuration'),
	path(r'plane_configurations/', views.ConfigurationView.as_view(), name='all_configurations'),	
	path(r'plane_configuration/<int:pk>/submit/', views.ConfigurationFormingView.as_view(), name='submit'),
	path(r'plane_configuration/<int:pk>/accept-reject/', views.ConfigurationCompletingView.as_view(), name='accept'),

	path(r'configuration_map/', views.ConfigurationMapView.as_view(), name="map"),
	
	path(r'users/', views.UsersList.as_view(), name='users-list'),
	path(r'user/<int:pk>/', views.UsersList.as_view(), name='user'),
	path(r'users/login/', views.UserLoginView.as_view(), name='user-login'),
	path(r'users/logout/', views.UserLogoutView.as_view(), name='user-logout'),
	
	
	
	# path('', views.getConfigurationElementsPage, name='configuration_elements')
	# path('plane_configuration_element/<int:id>/', views.getConfigurationElementPage, name='configuration_element'),
	# path('plane_configuration/<int:id>/', views.getConfigurationPage, name='configuration'),
	# path('delete_plane_configuration/<int:id>/', views.deleteConfiguration, name='delete_configuration'),
	# path('add_plane_configuration_element/<int:element_id>/', views.addConfigurationElement, name='add_element_to_configuration'),
]
