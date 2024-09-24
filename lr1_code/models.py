from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ConfigurationElement(models.Model):
    name = models.CharField(max_length=255)  # Наименование услуги
    price = models.DecimalField(max_digits=12, decimal_places=2)  # Цена услуги
    key_info = models.CharField(max_length=255)  # Основная информация (например, пассажировместимость)
    category = models.CharField(max_length=255)  # Категория услуги (например, компоновка салона)
    image = models.URLField(default='')  # URL изображения услуги
    detail_text = models.TextField(default='There is no detail text')  # Подробное описание услуги
    is_deleted = models.BooleanField(default=False)  # Статус услуги (удалена/действует)
    
    class Meta:
        db_table = 'configuration_elements'  # Название таблицы по предметной области


class Configuration(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('deleted', 'Удалёна'),
        ('created', 'Сформирована'),
        ('completed', 'Завершёна'),
        ('rejected', 'Отклонёна')
    ]
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')  # Статус заявки
    created_at = models.DateTimeField(default=timezone.now)  # Дата создания
    updated_at = models.DateTimeField(auto_now=True)  # Дата последнего обновления
    completed_at = models.DateTimeField(null=True, blank=True)  # Дата завершения
    customer_name = models.CharField(max_length=255)  # Имя клиента
    customer_phone = models.CharField(max_length=20)  # Телефон клиента
    customer_email = models.EmailField()  # Email клиента
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Итоговая цена
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_configurations')  # Создатель
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='moderated_configurations')  # Модератор
    
    class Meta:
        db_table = 'configurations'

    def calculate_total_price(self):
        # Рассчитываем общую стоимость всех услуг для этой заявки
        total = sum(plane.element.price for plane in self.planes.all())
        self.total_price = total
        self.save()


    
class Plane(models.Model):
    id = models.AutoField(primary_key=True)
    configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE)  # Заявка
    element = models.ForeignKey(ConfigurationElement, on_delete=models.CASCADE)  # Комплектация
    plane = models.CharField(max_length=255, default='Global 7500')

    class Meta:
        db_table = 'planes'
        unique_together = ('configuration', 'element')  # Составной первичный ключ