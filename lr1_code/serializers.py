from multiprocessing.managers import BaseManager
from argon2 import hash_password
from lr1_code.models import ConfigurationElement, Configuration, ConfigurationMap, AuthUser, UserManager
from rest_framework import serializers
from collections import OrderedDict

class ConfigurationElementSerializer(serializers.ModelSerializer):
    class Meta:
        # Модель, которую мы сериализуем
        model = ConfigurationElement
        # Поля, которые мы сериализуем
        fields = ['pk', 'name', 'price', 'key_info', 'category', 'image', 'detail_text', 'is_deleted']


class ConfigurationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        # Модель, которую мы сериализуем
        model = Configuration
        # Поля, которые мы сериализуем
        fields = ['pk', 'status', 'created_at', 'updated_at', 'completed_at', 'customer_name', 'customer_phone', 'customer_email', 'total_price', 'creator', 'moderator', 'plane', 'user']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 


class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = AuthUser
        fields = '__all__'  # Это будет включать все поля вашей модели

    def create(self, validated_data):
        # Создаем пользователя и устанавливаем пароль
        user = AuthUser(**validated_data)
        user.set_password(validated_data['password'])  # Убедитесь, что вы хэшируете пароль
        user.save()
        return user

class ConfigurationMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurationMap
        fields = '__all__'
