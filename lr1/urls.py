from django.contrib import admin
from django.urls import path
from lr1_code import views

urlpatterns = [
    path('admin/', admin.site.urls),
	path('', views.getStartPage, name="start"),
	path('main/', views.getMainPage, name='main'),
	# path('detail/', views.getDetailPage),
	# path('configuration/', views.getConfigurationPage),
	path('detail/<int:id>/', views.getDetailPage, name='detail_url'),
	path('configuration/<int:id>/', views.getConfigurationPage, name='configuration_url')
]
