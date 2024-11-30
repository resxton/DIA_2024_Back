# Django и сторонние библиотеки
from argparse import Action
from datetime import timezone
import uuid

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.db import connection
from django.db.models import F
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, SAFE_METHODS, IsAuthenticatedOrReadOnly
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import authentication_classes, action
from rest_framework.utils.serializer_helpers import ReturnDict
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
import redis

# Модели
from lr1_code.models import Configuration, ConfigurationElement, ConfigurationMap, AuthUser

# Сериализаторы
from lr1_code.permissions import IsAdmin
from lr1_code.serializers import ConfigurationElementSerializer, ConfigurationSerializer, UserSerializer, ConfigurationMapSerializer

# Утилиты
from lr1_code.minio import *
from lr1_code.permissions import *

# Connect to our Redis instance
session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

def user():
    try:
        user1 = AuthUser.objects.get(id=1)
    except:
        user1 = AuthUser(id=1, first_name="John", last_name="Doe", password=1234, username="user1")
        user1.save()
    return user1

class ConfigurationElementsView(APIView):
    model_class = ConfigurationElement
    serializer_class = ConfigurationElementSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
    request_body=ConfigurationElementSerializer,
    operation_summary="Создать новый элемент конфигурации",
    responses={
        201: openapi.Response('Created', ConfigurationElementSerializer),
        400: openapi.Response('Bad Request'),
        401: openapi.Response('Unauthorized'),
        403: openapi.Response('Forbidden'),
    }
    )
    def post(self, request, format=None):
        # Получаем куку session_id безопасно
        ssid = request.COOKIES.get("session_id")
        if not ssid:
            return Response(
                {"error": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем наличие пользователя в хранилище сессий
        user_id = session_storage.get(ssid)
        if not user_id:
            return Response(
                {"error": "Сессия недействительна."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем существование пользователя в базе
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response(
                {"error": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Проверка прав пользователя
        if not (user_instance.is_superuser or user_instance.is_staff):
            return Response(
                {"detail": "Доступ запрещен."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Валидация данных
        serializer = ConfigurationElementSerializer(data=request.data)
        if serializer.is_valid():
            # Сохраняем новый элемент конфигурации
            configuration_element = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(
            {"error": "Ошибка валидации.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )



    @swagger_auto_schema(
        operation_summary="Получить список элементов с фильтрацией и добавлением id заявки-черновика"
    )
    def get(self, request, format=None):
        # Получаем куку session_id
        session_id = request.COOKIES.get("session_id")
        if not session_id:
            return Response(
                {"error": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем наличие пользователя в хранилище сессий
        user_id = session_storage.get(session_id)
        if not user_id:
            return Response(
                {"error": "Сессия недействительна."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем существование пользователя в базе
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response(
                {"error": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ищем черновик конфигурации для текущего пользователя
        draft_configuration = Configuration.objects.filter(
            status='draft', creator=user_instance
        ).first()

        # Получаем параметры фильтрации из запроса
        category = request.query_params.get('category')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')

        # Получаем элементы конфигурации
        configuration_elements = self.model_class.objects.all()

        if category:
            configuration_elements = configuration_elements.filter(category=category)

        if price_min:
            try:
                configuration_elements = configuration_elements.filter(price__gte=float(price_min))
            except ValueError:
                return Response(
                    {"error": "Неверный формат минимальной цены."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if price_max:
            try:
                configuration_elements = configuration_elements.filter(price__lte=float(price_max))
            except ValueError:
                return Response(
                    {"error": "Неверный формат максимальной цены."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Сериализация элементов
        serializer = self.serializer_class(configuration_elements, many=True)

        # Подсчитываем количество элементов в ConfigurationMap для черновика
        draft_elements_count = (
            ConfigurationMap.objects.filter(configuration_id=draft_configuration.id).count()
            if draft_configuration
            else 0
        )

        # Формируем ответ
        response_data = {
            "draft_configuration_id": draft_configuration.id if draft_configuration else None,
            "draft_elements_count": draft_elements_count,
            "configuration_elements": serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)



    
class ConfigurationElementView(APIView):
    model_class = ConfigurationElement
    serializer_class = ConfigurationElementSerializer

    @swagger_auto_schema(
        operation_summary="Получить информацию об элементе конфигурации по его идентификатору"
    )
    # Возвращает информацию об элементе
    def get(self, request, pk, format=None):
        configuration_element = get_object_or_404(self.model_class, pk=pk)
        serializer = self.serializer_class(configuration_element)
        return Response(serializer.data)

    @swagger_auto_schema(
    operation_summary="Удалить элемент конфигурации и связанное с ним изображение"
    )
    def delete(self, request, pk, format=None):
        # Проверяем сессию через куки
        session_id = request.COOKIES.get("session_id")
        if not session_id:
            return Response(
                {"error": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Получаем ID пользователя из хранилища сессий
        user_id = session_storage.get(session_id)
        if not user_id:
            return Response(
                {"error": "Сессия недействительна."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем существование пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response(
                {"error": "Пользователь не найден."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем права пользователя
        if user_instance.is_superuser or user_instance.is_staff:
            # Администраторы и менеджеры могут удалять любые элементы
            pass
        else:
            # Получаем элемент конфигурации
            configuration_element = get_object_or_404(self.model_class, pk=pk)

            # Проверяем, является ли пользователь создателем элемента
            if configuration_element.creator != user_instance:
                return Response(
                    {"detail": "Доступ запрещён."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Удаляем изображение, если оно существует
        if configuration_element.image:
            image_name = configuration_element.image.split('/')[-1]
            delete_result = delete_pic(image_name)
            if 'error' in delete_result:
                return Response(
                    {"error": f"Ошибка при удалении изображения: {delete_result['error']}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Удаляем сам элемент конфигурации
        configuration_element.delete()

        return Response(
            {"detail": "Элемент успешно удалён."},
            status=status.HTTP_204_NO_CONTENT
        )

    
    @swagger_auto_schema(
    request_body=None,
    operation_summary="Добавить элемент в заявку-черновик пользователя",
    responses={
        201: openapi.Response("Элемент успешно добавлен в заявку."),
        400: openapi.Response("Ошибка добавления элемента."),
        401: openapi.Response("Необходима аутентификация."),
    }
    )
    def post(self, request, pk):
        # Получаем session_id из куки
        session_id = request.COOKIES.get("session_id")
        if not session_id:
            return Response(
                {"error": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем наличие пользователя в хранилище сессий
        user_id = session_storage.get(session_id)
        if not user_id:
            return Response(
                {"error": "Сессия недействительна."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем существование пользователя в базе
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response(
                {"error": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Проверяем, есть ли текущая заявка-черновик у пользователя
        configuration = Configuration.objects.filter(creator=user_instance, status="draft").first()

        # Если заявки нет, создаём новую
        if not configuration:
            configuration = Configuration.objects.create(
                status="draft",
                creator=user_instance,
                customer_name=user_instance.first_name,
                customer_email=user_instance.email,
                created_at=timezone.now()
            )

        # Проверяем, добавлен ли уже элемент в конфигурацию
        existing_element = ConfigurationMap.objects.filter(
            configuration_id=configuration.id,
            element_id=pk
        ).exists()

        if existing_element:
            return Response(
                {"error": "Этот элемент уже добавлен в конфигурацию."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Добавляем элемент в заявку
        ConfigurationMap.objects.create(
            configuration_id=configuration.id,
            element_id=pk,
            count=1  # Значение по умолчанию
        )

        return Response(
            {"message": "Элемент успешно добавлен в заявку."},
            status=status.HTTP_201_CREATED
        )





class ConfigurationElementEditingView(APIView):
    model_class = ConfigurationElement
    serializer_class = ConfigurationElementSerializer

    permission_classes = [AllowAny]

    @swagger_auto_schema(
    request_body=ConfigurationElementSerializer,
    operation_summary="Обновить информацию об элементе конфигурации",
    responses={
        200: openapi.Response('Success', ConfigurationElementSerializer),
        400: openapi.Response('Bad Request'),
        401: openapi.Response('Необходима аутентификация.'),
        403: openapi.Response('Доступ запрещен.'),
        404: openapi.Response('Элемент конфигурации не найден.')
    }
    )
    def put(self, request, pk, format=None):
        # Получаем session_id из куки
        session_id = request.COOKIES.get("session_id")
        if not session_id:
            return Response(
                {"error": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем наличие пользователя в хранилище сессий
        user_id = session_storage.get(session_id)
        if not user_id:
            return Response(
                {"error": "Сессия недействительна."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем существование пользователя в базе
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response(
                {"error": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Проверка прав доступа (доступ только суперпользователям или сотрудникам)
        if not (user_instance.is_superuser or user_instance.is_staff):
            return Response(
                {"error": "Доступ запрещен."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем элемент конфигурации
        configuration_element = get_object_or_404(self.model_class, pk=pk)

        # Сериализуем данные для обновления
        serializer = self.serializer_class(configuration_element, data=request.data, partial=True)

        # Обработка изменения фото
        if 'pic' in serializer.initial_data:
            pic_result = add_pic(configuration_element, serializer.initial_data['pic'])
            if 'error' in pic_result.data:
                return Response(pic_result.data, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем валидность данных
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Возвращаем ошибки валидации
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @swagger_auto_schema(
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'pic': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY),
        },
    ),
    responses={
        200: openapi.Response('Success', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'message': openapi.Schema(type=openapi.TYPE_STRING)})),
        400: openapi.Response('Bad Request'),
        401: openapi.Response('Необходима аутентификация.'),
        403: openapi.Response('Доступ запрещен.'),
        404: openapi.Response('Элемент конфигурации не найден.'),
    },
    operation_summary="Заменить изображение элемента конфигурации, удалив предыдущее"
    )
    def post(self, request, pk, format=None):
        # Получаем session_id из куки
        session_id = request.COOKIES.get("session_id")
        if not session_id:
            return Response(
                {"error": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем наличие пользователя в хранилище сессий
        user_id = session_storage.get(session_id)
        if not user_id:
            return Response(
                {"error": "Сессия недействительна."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Проверяем существование пользователя в базе
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response(
                {"error": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Проверка прав доступа (доступ только суперпользователям или сотрудникам)
        if not (user_instance.is_superuser or user_instance.is_staff):
            return Response(
                {"error": "Доступ запрещен."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем элемент конфигурации
        configuration_element = get_object_or_404(self.model_class, pk=pk)

        # Проверяем наличие нового изображения
        if 'pic' in request.data:
            # Удаляем старое изображение, если оно существует
            if configuration_element.image:
                delete_result = delete_pic(configuration_element.image.split("/")[-1])  # Удаляем изображение по имени
                if 'error' in delete_result:
                    return Response(delete_result, status=status.HTTP_400_BAD_REQUEST)

            # Загружаем новое изображение
            pic_result = add_pic(configuration_element, request.data['pic'])
            if 'error' in pic_result.data:
                return pic_result

        return Response({"message": "Изображение успешно обновлено"}, status=status.HTTP_200_OK)



class ConfigurationView(APIView):
    model_class = Configuration
    serializer_class = ConfigurationSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
    operation_summary="Получить список конфигураций с возможностью фильтрации по статусу и дате создания"
    )
    def get(self, request, format=None):
        # Получаем session_id из куки
        session_id = request.COOKIES.get("session_id")
        if not session_id:
            return Response({"error": "Необходима аутентификация."}, status=status.HTTP_401_UNAUTHORIZED)

        # Проверяем сессию
        user_id = session_storage.get(session_id)
        if not user_id:
            return Response({"error": "Сессия недействительна."}, status=status.HTTP_401_UNAUTHORIZED)

        # Проверяем существование пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response({"error": "Пользователь не найден."}, status=status.HTTP_400_BAD_REQUEST)

        # Фильтруем конфигурации в зависимости от роли пользователя
        if user_instance.is_superuser or user_instance.is_staff:
            # Для администраторов: исключаем удалённые и черновики
            configurations = self.model_class.objects.exclude(status__in=['deleted', 'draft'])
        else:
            # Для обычных пользователей: возвращаем только их конфигурации
            configurations = self.model_class.objects.filter(creator=user_instance).exclude(status__in=['deleted', 'draft'])

        # Получаем параметры фильтрации из запроса
        status_filter = request.query_params.get('status')
        created_after = request.query_params.get('created_after')
        created_before = request.query_params.get('created_before')

        # Применяем фильтрацию по статусу
        if status_filter:
            configurations = configurations.filter(status=status_filter)

        # Применяем фильтрацию по дате создания
        if created_after:
            configurations = configurations.filter(created_at__gte=created_after)
        if created_before:
            configurations = configurations.filter(created_at__lte=created_before)

        # Сериализация конфигураций
        serializer = self.serializer_class(configurations, many=True)
        configurations_with_usernames = []

        # Добавляем имена пользователей в данные
        for config in serializer.data:
            creator_username = AuthUser.objects.get(id=config['creator']).username if config['creator'] else None
            moderator_username = AuthUser.objects.get(id=config['moderator']).username if config['moderator'] else None

            configurations_with_usernames.append({
                **config,
                "creator": creator_username,
                "moderator": moderator_username
            })

        return Response({"configurations": configurations_with_usernames}, status=status.HTTP_200_OK)




class ConfigurationDetailView(APIView):
    model_class = Configuration
    serializer_class = ConfigurationSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Получить конфигурацию по идентификатору с её элементами и изображениями"
    )
    def get(self, request, pk, format=None):
        # Получаем конфигурацию по id
        configuration = get_object_or_404(
            self.model_class.objects.prefetch_related('configurationmap_set__element'), pk=pk
        )

        # Безопасно получаем session_id из cookies
        ssid = request.COOKIES.get("session_id")
        if not ssid:
            return Response({"error": "Необходима аутентификация."}, status=status.HTTP_401_UNAUTHORIZED)

        # Проверяем сессию в хранилище
        user_id = session_storage.get(ssid)
        if not user_id:
            return Response({"error": "Сессия недействительна."}, status=status.HTTP_401_UNAUTHORIZED)

        # Проверяем существование пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response({"error": "Пользователь не найден."}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем права доступа
        if not (user_instance.is_superuser or user_instance.is_staff or configuration.creator == user_instance):
            return Response({'detail': 'Доступ запрещен.'}, status=status.HTTP_403_FORBIDDEN)

        # Сериализуем конфигурацию
        serializer = self.serializer_class(configuration)

        # Получаем услуги и их изображения
        configuration_elements = [
            {
                "service_name": map.element.name,
                "image": map.element.image if map.element.image else None,
                "price": map.element.price,
                "key_info": map.element.key_info,
                "category": map.element.category,
                "detail_text": map.element.detail_text,
            }
            for map in configuration.configurationmap_set.all()
        ]

        # Возвращаем данные с конфигурацией и списком услуг
        return Response({
            "configuration": serializer.data,
            "configuration_elements": configuration_elements
        }, status=status.HTTP_200_OK)

    
    @swagger_auto_schema(
        request_body=ConfigurationSerializer,
        responses={
            200: openapi.Response('Success', ConfigurationSerializer),
            400: openapi.Response('Bad Request'),
        },
        operation_summary="Обновить конфигурацию по идентификатору"
    )
    def put(self, request, pk, format=None):
        # Получаем куку sessionid
        ssid = request.COOKIES.get("sessionid")
        if ssid is None:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем user_id из хранилища сессий
        user_id = session_storage.get(ssid)
        if user_id is None:
            return Response({"error": "User session is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем существование пользователя в базе
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if not user_instance:
            return Response({"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка прав пользователя (только администратор или стафф)
        if not (user_instance.is_superuser or user_instance.is_staff):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем конфигурацию по id
        configuration = get_object_or_404(self.model_class, pk=pk)

        # Обновляем поля конфигурации
        serializer = self.serializer_class(configuration, data=request.data, partial=True)  # partial=True для частичного обновления

        if serializer.is_valid():
            serializer.save()  # Сохраняем изменения
            return Response(serializer.data, status=status.HTTP_200_OK)  # Возвращаем обновленные данные
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # Если есть ошибки валидации



    @swagger_auto_schema(
        operation_summary="Удалить конфигурацию, обновив её статус на 'deleted'"
    )
    def delete(self, request, pk, format=None):
        # Получаем session_id из куки
        ssid = request.COOKIES.get("sessionid")
        
        # Если session_id отсутствует или не валиден
        if not ssid or not session_storage.get(ssid):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем пользователя из хранилища сессий
        user_id = session_storage.get(ssid)
        user_instance = AuthUser.objects.filter(pk=user_id).first()

        # Проверяем, существует ли пользователь и имеет ли он необходимые права
        if not user_instance or not (user_instance.is_superuser or user_instance.is_staff):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем конфигурацию по id
        configuration = get_object_or_404(self.model_class, pk=pk)

        # Обновляем статус конфигурации на 'deleted'
        configuration.status = 'deleted'
        configuration.save()

        # Возвращаем успешный ответ
        return Response({"message": "Configuration status updated to deleted."}, status=status.HTTP_200_OK)



class ConfigurationFormingView(APIView):
    model_class = Configuration
    serializer_class = ConfigurationSerializer

    @swagger_auto_schema(
    request_body=ConfigurationSerializer,
    operation_summary="Сформировать заявку, обновив её статус на 'Сформирована'"
    )
    def put(self, request, pk, format=None):
        # Проверяем наличие sessionid в куки
        ssid = request.COOKIES.get("sessionid")
        
        if not ssid:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем user_id из хранилища сессий
        user_id = session_storage.get(ssid)
        if not user_id:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        # Получаем пользователя по user_id
        user = get_object_or_404(AuthUser, pk=user_id)
        
        # Устанавливаем пользователя в request
        request.user = user

        # Получаем конфигурацию по ID
        configuration = get_object_or_404(Configuration, pk=pk)

        # Проверяем права доступа
        if not (user.is_superuser or user.is_staff) and configuration.creator != user:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Проверяем, что заявка имеет статус "Черновик"
        if configuration.status != 'draft':
            return Response({'error': 'Заявка может быть сформирована только в статусе "Черновик"'}, status=status.HTTP_403_FORBIDDEN)

        # Устанавливаем новый статус заявки
        configuration.status = 'created'
        configuration.moderator = user  # Устанавливаем модератора
        configuration.updated_at = timezone.now()  # Обновляем дату изменения

        # Подсчитываем итоговую стоимость
        configuration.calculate_total_price()

        # Сохраняем изменения
        configuration.save()

        # Возвращаем обновленные данные конфигурации
        serializer = ConfigurationSerializer(configuration)
        return Response(serializer.data, status=status.HTTP_200_OK)



class ConfigurationCompletingView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=ConfigurationSerializer,
        operation_summary="Завершить или отклонить заявку, обновив её статус"
    )
    def put(self, request, pk, format=None):
        # Получаем sessionid из куки
        ssid = request.COOKIES.get("sessionid")
        if ssid is None:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        # Получаем пользователя из хранилища сессий
        user_id = session_storage.get(ssid)
        if user_id is None:
            return Response({'error': 'No user found for the session'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Загружаем пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if user_instance is None:
            return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем конфигурацию по ID
        configuration = get_object_or_404(Configuration, pk=pk)

        # Проверяем статус конфигурации
        if configuration.status != 'created':
            return Response({'error': 'Заявка может быть завершена или отклонена только в статусе "Сформирована"'}, status=status.HTTP_403_FORBIDDEN)

        # Проверяем допустимость статуса в запросе
        new_status = request.data.get('status')
        if new_status not in ['completed', 'rejected']:
            return Response({'error': 'Недопустимый статус. Ожидался статус "Завершёна" или "Отклонёна"'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем права пользователя
        if user_instance.is_superuser or user_instance.is_staff:
            # Устанавливаем новый статус и другие данные
            configuration.status = new_status
            configuration.moderator = user_instance  # Устанавливаем текущего пользователя как модератора
            configuration.completed_at = timezone.now()  # Устанавливаем дату завершения
            configuration.save()

            # Возвращаем обновленные данные конфигурации
            serializer = ConfigurationSerializer(configuration)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)


class ConfigurationMapView(APIView):
    model_class = ConfigurationMap
    serializer_class = ConfigurationMapSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'configuration_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'element_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    ),
    responses={
        204: openapi.Response('No Content'),
        400: openapi.Response('Bad Request'),
    },
    operation_summary="Удалить элемент из конфигурации по идентификаторам"
    )
    def delete(self, request, format=None):
        # Получаем sessionid из куки
        ssid = request.COOKIES.get("sessionid")
        if ssid is None:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем пользователя из хранилища сессий
        user_id = session_storage.get(ssid)
        if user_id is None:
            return Response({'error': 'No user found for the session'}, status=status.HTTP_400_BAD_REQUEST)

        # Загружаем пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if user_instance is None:
            return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)

        # Извлекаем параметры из запроса
        configuration_id = request.query_params.get('configuration_id')
        element_id = request.query_params.get('element_id')

        # Проверка на наличие необходимых параметров
        if not configuration_id or not element_id:
            return Response(
                {"error": "Both configuration_id and element_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем конфигурацию по ID
        configuration = get_object_or_404(Configuration, pk=configuration_id)

        # Проверка прав доступа пользователя
        if not (user_instance.is_superuser or user_instance.is_staff or configuration.creator == user_instance):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем объект ConfigurationMap по configuration и element
        configuration_map = get_object_or_404(
            self.model_class,
            configuration_id=configuration_id,
            element_id=element_id
        )

        # Удаляем объект ConfigurationMap
        configuration_map.delete()

        return Response({"message": "Element removed from configuration successfully."}, status=status.HTTP_204_NO_CONTENT)


    @swagger_auto_schema(
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'count': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    ),
    responses={
        200: openapi.Response('Success', ConfigurationMapSerializer),
        400: openapi.Response('Bad Request'),
    },
    operation_summary="Обновить количество элемента в конфигурации"
    )
    def put(self, request, format=None):
        # Получаем sessionid из куки
        ssid = request.COOKIES.get("sessionid")
        if ssid is None:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем пользователя из хранилища сессий
        user_id = session_storage.get(ssid)
        if user_id is None:
            return Response({'error': 'No user found for the session'}, status=status.HTTP_400_BAD_REQUEST)

        # Загружаем пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if user_instance is None:
            return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)

        # Извлекаем параметры из запроса
        configuration_id = request.query_params.get('configuration_id')
        element_id = request.query_params.get('element_id')

        # Проверка на наличие необходимых параметров
        if not configuration_id or not element_id:
            return Response(
                {"error": "Both configuration_id and element_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем объект Configuration по ID
        configuration = get_object_or_404(Configuration, pk=configuration_id)

        # Проверка прав доступа пользователя
        if not (user_instance.is_superuser or user_instance.is_staff or configuration.creator == user_instance):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем объект ConfigurationMap
        configuration_map = get_object_or_404(
            self.model_class,
            configuration_id=configuration_id,
            element_id=element_id
        )

        # Обновляем только те поля, которые переданы в запросе
        serializer = self.serializer_class(configuration_map, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()  # Сохраняем изменения
            return Response(serializer.data, status=status.HTTP_200_OK)  # Возвращаем обновленные данные

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class UsersList(APIView):
    model_class = AuthUser
    serializer_class = UserSerializer

    @swagger_auto_schema(
    operation_summary="Получить список всех пользователей"
    )
    def get(self, request, format=None):
        # Получаем sessionid из куки
        ssid = request.COOKIES.get("sessionid")
        if ssid is None:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем пользователя из хранилища сессий
        user_id = session_storage.get(ssid)
        if user_id is None:
            return Response({'error': 'No user found for the session'}, status=status.HTTP_400_BAD_REQUEST)

        # Загружаем пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if user_instance is None:
            return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, является ли пользователь администратором или сотрудником
        if not user_instance.is_superuser:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем всех пользователей
        users = self.objects.all()
        serializer = self.serializer_class(users, many=True)
        return Response(serializer.data)

    
    @swagger_auto_schema(
        request_body=UserSerializer,
        operation_summary="Создать нового пользователя"
    )
    def post(self, request, format=None):
        # Получаем sessionid из куки
        ssid = request.COOKIES.get("sessionid")
        if ssid is None:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем пользователя из хранилища сессий
        user_id = session_storage.get(ssid)
        if user_id is None:
            return Response({'error': 'No user found for the session'}, status=status.HTTP_400_BAD_REQUEST)

        # Загружаем пользователя
        user_instance = AuthUser.objects.filter(pk=user_id).first()
        if user_instance is None:
            return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, является ли пользователь администратором
        if not user_instance.is_superuser:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Сериализуем данные пользователя
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            if self.model_class.objects.filter(username=username).exists():
                return Response(
                    {"error": "Пользователь с таким именем уже существует."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Хешируем пароль перед сохранением
            password = serializer.validated_data.get('password')
            if password:
                serializer.validated_data['password'] = make_password(password)  # Хеширование пароля

            # Сохраняем пользователя
            user = self.model_class(**serializer.validated_data)

            # Устанавливаем значения по умолчанию для обязательных полей
            user.is_superuser = False  # Установите значение по умолчанию
            user.is_staff = False  # Установите значение по умолчанию
            user.is_active = True  # Установите значение по умолчанию
            user.date_joined = timezone.now()  # Устанавливаем текущую дату и время

            user.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @swagger_auto_schema(
    request_body=UserSerializer,
    operation_summary="Обновить информацию о пользователе"
    )
    def put(self, request, pk, format=None):
        # Получаем sessionid из куки
        ssid = request.COOKIES.get("sessionid")
        if ssid is None:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем пользователя из хранилища сессий
        user_id = session_storage.get(ssid)
        if user_id is None:
            return Response({'error': 'No user found for the session'}, status=status.HTTP_400_BAD_REQUEST)

        # Загружаем пользователя
        current_user = AuthUser.objects.filter(pk=user_id).first()
        if current_user is None:
            return Response({'error': 'No such user'}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем пользователя для обновления
        user = get_object_or_404(self.model_class, pk=pk)

        # Проверяем права доступа - только текущий пользователь или администратор
        if current_user.is_superuser or current_user == user:
            pass
        else:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Сериализуем данные с обновлением
        serializer = self.serializer_class(user, data=request.data, partial=True)

        if serializer.is_valid():
            # Если пароль изменен, хешируем его
            password = serializer.validated_data.get('password')
            if password:
                serializer.validated_data['password'] = make_password(password)

            # Сохраняем обновленные данные
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class UserLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Response('Вход успешен.'),
            401: openapi.Response('Неверные данные.'),
        },
        operation_summary="Войти в систему"
    )
    def post(self, request, format=None):
        username = request.data.get('username')
        password = request.data.get('password')

        # Проверка наличия данных
        if not username or not password:
            return Response({"error": "Необходимо указать имя пользователя и пароль."}, status=status.HTTP_400_BAD_REQUEST)

        # Аутентификация
        user = authenticate(username=username, password=password)

        if user is not None:
            random_key = str(uuid.uuid4())
            session_storage.set(random_key, user.pk)

            # Ответ с установкой куки
            response = Response({"message": "Вход успешен."}, status=status.HTTP_200_OK)
            response.set_cookie("session_id", random_key, httponly=True, secure=False)  
            return response

        return Response({"error": "Неверные данные."}, status=status.HTTP_401_UNAUTHORIZED)




class UserLogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Выход успешен.'),
        },
        operation_summary="Выйти из системы"
    )
    def post(self, request):
        session_id = request.COOKIES.get('session_id')
        if session_id:
            session_storage.delete(session_id)  # Удалите из вашего хранилища
            response = Response({"message": "Вы вышли из системы."}, status=status.HTTP_200_OK)
            response.delete_cookie("session_id")  # Удалите куку
            return response
        return Response({"error": "Необходима аутентификация."}, status=status.HTTP_401_UNAUTHORIZED)



class UserViewSet(viewsets.ModelViewSet):
    """
    Класс, описывающий методы работы с пользователями.
    Осуществляет связь с таблицей пользователей в базе данных.
    """
    queryset = AuthUser.objects.all()
    serializer_class = UserSerializer
    model_class = AuthUser

    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = [AllowAny]
        elif self.action in ['list']:
            permission_classes = [IsAdmin | IsManager]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        """
        Функция регистрации новых пользователей.
        Если пользователя с указанным username ещё нет, в БД будет добавлен новый пользователь.
        """
        if self.model_class.objects.filter(username=request.data['username']).exists():
            return Response({'status': 'Exist'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            self.model_class.objects.create_user(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
                email=serializer.validated_data.get('email', ''),
                is_superuser=serializer.validated_data.get('is_superuser', False),
                is_staff=serializer.validated_data.get('is_staff', False)
            )
            return Response({'status': 'Success'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes        
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator

def check_session(request):
    session_id = request.COOKIES.get("sessionid")
    print(session_id)
    if session_id is None:
        return None  # Сессия не найдена

    pk = session_storage.get(session_id)
    if pk is None:
        return None  # Сессия невалидна или истекла

    return pk
