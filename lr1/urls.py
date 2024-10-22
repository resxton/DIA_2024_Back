# Стандартные библиотеки Django
from django.contrib import admin
from django.urls import path, include

# Сторонние библиотеки
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Локальные модули
from lr1_code import views


router = routers.DefaultRouter()

schema_view = get_schema_view(
   openapi.Info(
      title="Configuration Management API",
      default_version='v1',
      description=(
          "API для управления конфигурациями и услугами. "
          "Позволяет создавать, обновлять и удалять конфигурации, "
          "а также управлять элементами услуг, связанными с ними. "
          "Поддерживает аутентификацию пользователей и предоставляет "
          "интерфейс для взаимодействия с данными о клиентах и их запросами."
      ),
      terms_of_service="https://www.nimbus.ru/terms/",
      contact=openapi.Contact(email="support@nimbus.ru"),
      license=openapi.License(name="BSD License")
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router.register(r'user', views.UserViewSet, basename='user')

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
	path(r'users/<int:pk>/', views.UsersList.as_view(), name='user'),

 	path('login/',  views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
	
	path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
	
	# path('', views.getConfigurationElementsPage, name='configuration_elements')
	# path('plane_configuration_element/<int:id>/', views.getConfigurationElementPage, name='configuration_element'),
	# path('plane_configuration/<int:id>/', views.getConfigurationPage, name='configuration'),
	# path('delete_plane_configuration/<int:id>/', views.deleteConfiguration, name='delete_configuration'),
	# path('add_plane_configuration_element/<int:element_id>/', views.addConfigurationElement, name='add_element_to_configuration'),
]
