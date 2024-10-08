from argon2 import hash_password
from lr1_code.models import ConfigurationElement, Configuration, ConfigurationMap, AuthUser
from rest_framework import serializers


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


class UserSerializer(serializers.ModelSerializer):
    configuration_set = ConfigurationSerializer(many=True, read_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = AuthUser
        fields = ["id", "first_name", "last_name", "username", "email", "password", "configuration_set"]

    def create(self, validated_data):
        # Создаем нового пользователя
        user = AuthUser(**validated_data)
        user.password = validated_data['password']
        user.save()
        return user


class ConfigurationMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurationMap
        fields = '__all__'