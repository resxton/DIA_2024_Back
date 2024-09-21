from django.db import connection
from django.http import Http404
from django.shortcuts import redirect, render
from lr1_code.models import ConfigurationElement, Configuration, Plane


def getStartPage(request):
    return render(request, 'start.html')


def getMainPage(request):
    # Получаем ID текущей заявки из сессии
    current_configuration_id = request.session.get('current_configuration_id')
    
    # Если ID существует, ищем заявку
    if current_configuration_id:
        current_configuration = Configuration.objects.filter(id=current_configuration_id, status='draft').first()
    else:
        current_configuration = None

    # Если текущей заявки нет, создаем новую
    if not current_configuration:
        current_configuration = Configuration.objects.create(
            status='draft',
            customer_name='',
            customer_phone='',
            customer_email=''
        )
        # Сохраняем ID новой заявки в сессии
        request.session['current_configuration_id'] = current_configuration.id

    category = request.GET.get('categories', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')

    # Фильтруем элементы конфигурации
    filtered_items = ConfigurationElement.objects.all()

    if category:
        filtered_items = filtered_items.filter(category=category)

    if price_min:
        filtered_items = filtered_items.filter(price__gte=float(price_min))

    if price_max:
        filtered_items = filtered_items.filter(price__lte=float(price_max))

    # Получаем идентификаторы элементов, связанных с текущей конфигурацией
    planes = Plane.objects.filter(configuration=current_configuration)
    configuration_counter = planes.count()  # Подсчитываем количество элементов в текущей заявке

    return render(request, 'main.html', {
        'configuration_elements': filtered_items,
        'configuration_counter': configuration_counter,  # Количество элементов в текущей заявке
        'selected_category': category,
        'selected_price_min': price_min,
        'selected_price_max': price_max,
        'current_configuration': current_configuration  # Передаем текущую заявку
    })



def getDetailPage(request, id):
    try:
        item = ConfigurationElement.objects.get(id=id)
    except ConfigurationElement.DoesNotExist:
        raise Http404('Элемент с таким id не найден')

    return render(request, 'detail.html', {
        'id': item.id,
        'name': item.name,
        'price': item.price,
        'key_info': item.key_info,
        'category': item.category,
        'image': item.image,
        'detail_text': item.detail_text
    })


def getConfigurationPage(request, id):
    try:
        configuration = Configuration.objects.get(id=id)
    except Configuration.DoesNotExist:
        raise Http404('Конфигурация с таким id не найдена')

    if configuration.status == 'deleted':
        return redirect('main')

    # Получаем самолеты, связанные с данной конфигурацией
    planes = Plane.objects.filter(configuration=configuration)

    if not planes.exists():
        raise Http404('Самолет для данной конфигурации не найден')

    # Получаем элементы конфигурации по идентификаторам
    config_elements_ids = planes.values_list('element_id', flat=True)
    config_elements = ConfigurationElement.objects.filter(id__in=config_elements_ids)

    return render(request, 'configuration.html', {
        'configuration_id': configuration.id,
        'customer_name': configuration.customer_name,
        'customer_phone': configuration.customer_phone,
        'customer_email': configuration.customer_email,
        'configuration_amount': configuration.total_price,
        'config_elements': config_elements,
        'plane_name': planes.first().plane if planes.exists() else 'Нет самолета'
    })

def deleteConfiguration(request, id):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("UPDATE configurations SET status = 'deleted' WHERE id = %s", [id])
            print("updated")
        return redirect('main')  # Перенаправление на главную страницу или на страницу с заявками
    else:
        return Http404('Метод не поддерживается')
    

def addConfigurationElement(request, element_id):
    # Получаем ID текущей заявки из сессии
    current_configuration_id = request.session.get('current_configuration_id')

    if not current_configuration_id:
        return redirect('main')  # Перенаправляем, если текущей заявки нет

    # Получаем текущую заявку
    configuration = Configuration.objects.filter(id=current_configuration_id, status='draft').first()
    
    if not configuration:
        return redirect('main')  # Перенаправляем, если заявка не найдена

    # Получаем элемент, который нужно добавить
    try:
        element = ConfigurationElement.objects.get(id=element_id)
    except ConfigurationElement.DoesNotExist:
        return redirect('main')  # Перенаправляем, если элемент не найден

    # Добавляем элемент в таблицу Plane
    Plane.objects.create(configuration_id=configuration.id, element_id=element.id, plane='')


    return redirect('main')  # Перенаправляем на страницу конфигурации
