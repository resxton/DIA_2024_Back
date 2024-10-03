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
    customer_email = models.CharField(max_length=255)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Итоговая цена
    creator = models.ForeignKey('AuthUser', models.DO_NOTHING, blank=True, null=True)
    moderator = models.ForeignKey('AuthUser', models.DO_NOTHING, related_name='configurations_moderator_set', blank=True, null=True)
    plane = models.CharField(max_length=255, default='Global 7500')

    class Meta:
        db_table = 'configurations'

    def calculate_total_price(self):
        # Рассчитываем общую стоимость всех услуг для этой заявки
        total = sum(plane.element.price for plane in self.planes.all())
        self.total_price = total
        self.save()


    
class ConfigurationMap(models.Model):
    id = models.AutoField(primary_key=True)
    configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE)  # Заявка
    element = models.ForeignKey(ConfigurationElement, on_delete=models.CASCADE)  # Комплектация
    count = models.IntegerField()

    class Meta:
        db_table = 'configuration_map'
        unique_together = ('configuration', 'element')  # Составной первичный ключ


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        managed = False
        db_table = 'auth_user'