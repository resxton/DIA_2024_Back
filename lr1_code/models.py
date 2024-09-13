from django.db import models

class ConfigurationElement(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    key_info = models.CharField(max_length=255)
    category = models.CharField(max_length=20)
    image_filename = models.CharField(max_length=255)  # Хранение имени файла изображения

    def __str__(self):
        return self.name

    def get_image_url(self):
        # Предполагаем, что вы храните изображения в MinIO по следующему пути
        base_url = 'http://127.0.0.1:9000/assets/'
        return f"{base_url}{self.image_filename}"


class Configuration(models.Model):
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField()
    elements = models.ManyToManyField(ConfigurationElement, related_name='configurations')

    def __str__(self):
        return f'Configuration for {self.customer_name}'