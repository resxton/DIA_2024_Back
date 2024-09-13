from django.contrib import admin
from .models import ConfigurationElement, Configuration

@admin.register(ConfigurationElement)
class ConfigurationElementAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'key_info', 'category', 'image_filename')

@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'customer_phone', 'customer_email')