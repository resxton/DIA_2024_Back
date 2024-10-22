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
    permission_classes = [IsAdmin | IsManager]

    model_class = ConfigurationElement
    serializer_class = ConfigurationElementSerializer

    @swagger_auto_schema(
        request_body=ConfigurationElementSerializer,
        operation_summary="Создать новый элемент конфигурации",
        responses={
            201: openapi.Response('Created', ConfigurationElementSerializer),
            400: openapi.Response('Bad Request'),
        }
    )
    def post(self, request, format=None):
        serializer = ConfigurationElementSerializer(data=request.data)
        if serializer.is_valid():
            # Сохраняем новый элемент конфигурации
            configuration_element = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Получить список элементов с фильтрацией и добавлением id заявки-черновика"
    )
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    # Возвращает список элементов с фильтрацией и добавлением id заявки-черновика
    def get(self, request, format=None):
        user_instance = user()
        draft_configuration = Configuration.objects.filter(status='draft', creator=user_instance).first()

        # Фильтруем элементы конфигурации по параметрам из запроса
        category = request.query_params.get('category', None)
        price_min = request.query_params.get('price_min', None)
        price_max = request.query_params.get('price_max', None)

        configuration_elements = self.model_class.objects.all()

        if category:
            configuration_elements = configuration_elements.filter(category=category)

        if price_min:
            configuration_elements = configuration_elements.filter(price__gte=float(price_min))

        if price_max:
            configuration_elements = configuration_elements.filter(price__lte=float(price_max))

        serializer = self.serializer_class(configuration_elements, many=True)

        # Подсчитываем количество элементов в таблице configuration_map с configuration_id, равным draft_id
        draft_elements_count = ConfigurationMap.objects.filter(configuration_id=draft_configuration.id).count() if draft_configuration else 0

        # Добавляем в результат id заявки-черновика и количество элементов в configuration_map
        response_data = {
            "draft_configuration_id": draft_configuration.id if draft_configuration else None,
            "draft_elements_count": draft_elements_count,
            "configuration_elements": serializer.data
        }

        return Response(response_data)



    
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
    # Удаляет информацию об элементе и связанное изображение
    def delete(self, request, pk, format=None):
        if request.user.is_superuser or request.user.is_staff:
            # Администраторы и менеджеры могут видеть все конфигурации
            pass
        else:
            # Если пользователь не создатель конфигурации, возвращаем 403
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        configuration_element = get_object_or_404(self.model_class, pk=pk)
        
        # Удаление изображения из Minio
        if configuration_element.image:
            image_name = configuration_element.image.split('/')[-1]
            delete_result = delete_pic(image_name)
            if 'error' in delete_result:
                return Response(delete_result, status=status.HTTP_400_BAD_REQUEST)

        # Удаление самого элемента
        configuration_element.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @swagger_auto_schema(
        request_body=ConfigurationElementSerializer,
        operation_summary="Добавить элемент в заявку-черновик пользователя"
    )
    def post(self, request, pk):
        # Проверяем, есть ли уже текущая заявка у пользователя
        configuration = Configuration.objects.filter(creator=request.user, status='draft').first()

        # Если текущей заявки нет, создаем новую
        if not configuration:
            configuration = Configuration.objects.create(
                status='draft',
                creator=request.user,  # Устанавливаем создателя заявки
                created_at=timezone.now()  # Устанавливаем дату создания
                # Другие обязательные поля можно добавить здесь
            )

        # Проверяем, есть ли уже этот элемент в заявке
        existing_element = ConfigurationMap.objects.filter(configuration_id=configuration.id, element_id=pk).exists()

        if existing_element:
            return Response({"error": "Этот элемент уже добавлен в конфигурацию."}, status=status.HTTP_400_BAD_REQUEST)

        # Добавляем элемент в таблицу ConfigurationMap
        ConfigurationMap.objects.create(configuration_id=configuration.id, element_id=pk, count=1)

        return Response({"message": "Элемент успешно добавлен в заявку."}, status=status.HTTP_201_CREATED)



class ConfigurationElementEditingView(APIView):
    model_class = ConfigurationElement
    serializer_class = ConfigurationElementSerializer

    permission_classes = [IsAdmin | IsManager]

    @swagger_auto_schema(
        request_body=ConfigurationElementSerializer,
        operation_summary="Обновить информацию об элементе конфигурации",
        responses={
            200: openapi.Response('Success', ConfigurationElementSerializer),
            400: openapi.Response('Bad Request'),
        }
    )
    # Обновляет информацию об элементе
    def put(self, request, pk, format=None):
        configuration_element = get_object_or_404(self.model_class, pk=pk)
        serializer = self.serializer_class(configuration_element, data=request.data, partial=True)
        # Изменение фото 
        if 'pic' in serializer.initial_data:
            pic_result = add_pic(configuration_element, serializer.initial_data['pic'])
            if 'error' in pic_result.data:
                return pic_result
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
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
        },
        operation_summary="Заменить изображение элемента конфигурации, удалив предыдущее"
    )
    # Заменяет картинку, удаляя предыдущую
    def post(self, request, pk, format=None):
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

    @swagger_auto_schema(
        operation_summary="Получить список конфигураций с возможностью фильтрации по статусу и дате создания"
    )
    def get(self, request, format=None):
        if request.user.is_authenticated:
            # Если пользователь аутентифицирован, проверяем его роль
            if request.user.is_superuser or request.user.is_staff:  # Для администраторов
                configurations = self.model_class.objects.exclude(status__in=['deleted', 'draft'])
            else:
                # Для создателей возвращаем только их заявки
                configurations = self.model_class.objects.filter(creator=request.user).exclude(status__in=['deleted', 'draft'])
        else:
            # Если пользователь не аутентифицирован, возвращаем 401/403
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Получаем параметры фильтрации из запроса
        status_filter = request.query_params.get('status', None)
        created_after = request.query_params.get('created_after', None)
        created_before = request.query_params.get('created_before', None)

        # Применяем фильтрацию по статусу, если параметр указан
        if status_filter:
            configurations = configurations.filter(status=status_filter)

        # Применяем фильтрацию по дате создания, если параметры указаны
        if created_after:
            configurations = configurations.filter(created_at__gte=created_after)
        if created_before:
            configurations = configurations.filter(created_at__lte=created_before)

        # Получаем сериализованные данные
        serializer = self.serializer_class(configurations, many=True)
        configurations_with_usernames = []

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
    permission_classes = [IsManager | IsAdmin]

    @swagger_auto_schema(
        operation_summary="Получить конфигурацию по идентификатору с её элементами и изображениями"
    )
    def get(self, request, pk, format=None):
        # Получаем конфигурацию по id
        configuration = get_object_or_404(self.model_class.objects.prefetch_related('configurationmap_set__element'), pk=pk)

        # Проверяем, имеет ли пользователь право доступа к данной конфигурации
        if request.user.is_superuser or request.user.is_staff:
            # Администраторы и менеджеры могут видеть все конфигурации
            pass
        elif configuration.creator != request.user:
            # Если пользователь не создатель конфигурации, возвращаем 403
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        # Сериализуем конфигурацию
        serializer = self.serializer_class(configuration)

        # Получаем услуги и их изображения
        configuration_elements = [
            {
                "service_name": map.element.name,
                "image": map.element.image,
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
        if request.user.is_superuser or request.user.is_staff:
            pass
        else:
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
        if request.user.is_superuser or request.user.is_staff:
            pass
        else:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        # Получаем конфигурацию по id
        configuration = get_object_or_404(self.model_class, pk=pk)

        # Обновляем статус на 'deleted'
        configuration.status = 'deleted'
        configuration.save()

        return Response({"message": "Configuration status updated to deleted."}, status=status.HTTP_200_OK)


class ConfigurationFormingView(APIView):
    model_class = Configuration
    serializer_class = ConfigurationSerializer

    @swagger_auto_schema(
        request_body=ConfigurationSerializer,
        operation_summary="Сформировать заявку, обновив её статус на 'Сформирована'"
    )
    def put(self, request, pk, format=None):
        username = check_session(request)
        print(username)
        # Здесь нужно получить пользователя по username
        user = get_object_or_404(AuthUser, username=username)
        request.user = user  # Устанавливаем пользователя в request

        # Далее стандартная логика
        # Получаем конфигурацию по ID
        configuration = get_object_or_404(Configuration, pk=pk)

        if request.user.is_superuser or request.user.is_staff:
            pass
        elif configuration.creator != request.user:
            # Если пользователь не создатель конфигурации, возвращаем 403
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        else:
            pass

        # Проверяем, что заявка имеет статус "Сформирована"
        if configuration.status != 'draft':
            return Response({'error': 'Заявка может быть сформирована только в статусе "Черновик"'}, status=status.HTTP_403_FORBIDDEN)

        # Устанавливаем новый статус заявки
        configuration.status = 'created'
        configuration.moderator = request.user  # Устанавливаем текущего пользователя как модератора
        configuration.updated_at = timezone.now()  # Устанавливаем дату изменения

        # Подсчитываем итоговую стоимость услуг для этой заявки
        configuration.calculate_total_price()

        # Сохраняем изменения в конфигурации
        configuration.save()

        # Возвращаем обновленные данные конфигурации
        serializer = ConfigurationSerializer(configuration)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConfigurationCompletingView(APIView):
    permission_classes = [IsAdmin | IsManager]
    
    @swagger_auto_schema(
        request_body=ConfigurationSerializer,
        operation_summary="Завершить или отклонить заявку, обновив её статус"
    )
    def put(self, request, pk, format=None):
        # Получаем конфигурацию по ID
        configuration = get_object_or_404(Configuration, pk=pk)

        # Проверяем, что заявка имеет статус "Сформирована"
        if configuration.status != 'created':
            return Response({'error': 'Заявка может быть завершена или отклонена только в статусе "Сформирована"'}, status=status.HTTP_403_FORBIDDEN)

        # Проверяем, что в запросе передан статус
        new_status = request.data.get('status')
        if new_status not in ['completed', 'rejected']:
            return Response({'error': 'Недопустимый статус. Ожидался статус "Завершёна" или "Отклонёна"'}, status=status.HTTP_400_BAD_REQUEST)

        # Устанавливаем новый статус заявки
        configuration.status = new_status
        configuration.moderator = request.user  # Устанавливаем текущего пользователя как модератора
        configuration.completed_at = timezone.now()  # Устанавливаем дату завершения

        # Сохраняем изменения в конфигурации
        configuration.save()

        # Возвращаем обновленные данные конфигурации
        serializer = ConfigurationSerializer(configuration)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ConfigurationMapView(APIView):
    model_class = ConfigurationMap
    serializer_class = ConfigurationMapSerializer
    permission_classes = [IsManager | IsAdmin]

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
        # Извлекаем параметры из запроса
        configuration_id = request.query_params.get('configuration_id')
        element_id = request.query_params.get('element_id')

        # Проверка на наличие необходимых параметров
        if not configuration_id or not element_id:
            return Response(
                {"error": "Both configuration_id and element_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

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
        # Извлекаем параметры из запроса
        configuration_id = request.query_params.get('configuration_id')
        element_id = request.query_params.get('element_id')

        # Проверка на наличие необходимых параметров
        if not configuration_id or not element_id:
            return Response(
                {"error": "Both configuration_id and element_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

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
        if request.user.is_superuser:
            pass
        else:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        user = self.objects.all()
        serializer = self.serializer_class(user, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        request_body=UserSerializer,
        operation_summary="Создать нового пользователя"
    )
    def post(self, request, format=None):
        if request.user.is_superuser:
            pass
        else:
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
            user.date_joined = timezone.now()  # Установите текущую дату и время

            user.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        request_body=UserSerializer,
        operation_summary="Обновить информацию о пользователе"
    )
    def put(self, request, pk, format=None):
        # Получаем пользователя по id
        user = get_object_or_404(self.model_class, pk=pk)

        if request.user.is_superuser or request.user == user:
            pass
        else:
            # Если пользователь не создатель конфигурации, возвращаем 403
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
        user = authenticate(username=username, password=password)
        print(username, password)
        if user is not None:
            random_key = str(uuid.uuid4())
            session_storage.set(random_key, username)

            response = HttpResponse("{'status': 'ok'}")
            response.set_cookie("session_id", random_key)

            login(request, user)
            return Response({"message": "Вход успешен."}, status=status.HTTP_200_OK)
        return Response({"error": "Неверные данные."}, status=status.HTTP_401_UNAUTHORIZED)


class UserLogoutView(APIView):
    authentication_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Выход успешен.'),
        },
        operation_summary="Выйти из системы"
    )
    def post(self, request, format=None):
        logout(request)
        return Response({"message": "Выход успешен."}, status=status.HTTP_200_OK)


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

    username = session_storage.get(session_id)
    if username is None:
        return None  # Сессия невалидна или истекла

    return username
