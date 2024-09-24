from django.contrib import admin
from .models import ConfigurationElement, Configuration, Plane

@admin.register(ConfigurationElement)
class ConfigurationElementAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'key_info', 'category', 'is_deleted')
    search_fields = ('name', 'category', 'price')
    list_filter = ('is_deleted',)

@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'status', 'created_at', 'updated_at', 'total_price')
    search_fields = ('customer_name', 'customer_email')
    list_filter = ('status',)

@admin.register(Plane)
class PlaneAdmin(admin.ModelAdmin):
    list_display = ('configuration', 'element', 'plane')
    search_fields = ('plane',)
    list_filter = ('configuration', 'element')

