from django.db import connection
from django.http import Http404
from django.shortcuts import redirect, render
from lr1_code.models import ConfigurationElement, Configuration, ConfigurationMap
from django.db.models import F


def getStartPage(request):
    return render(request, 'start.html')


def getConfigurationElementsPage(request):
    # Получаем ID текущей заявки из сессии
    current_configuration_id = request.session.get('current_configuration_id')
    
    # Если ID существует, ищем заявку
    if current_configuration_id:
        current_configuration = Configuration.objects.filter(id=current_configuration_id, status='draft').first()
    else:
        current_configuration = None

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
    elements = ConfigurationMap.objects.filter(configuration=current_configuration)
    configuration_counter = elements.count()  # Подсчитываем количество элементов в текущей заявке

    return render(request, 'main.html', {
        'configuration_elements': filtered_items,
        'configuration_counter': configuration_counter,  # Количество элементов в текущей заявке
        'selected_category': category,
        'selected_price_min': price_min,
        'selected_price_max': price_max,
        'current_configuration': current_configuration  # Передаем текущую заявку
    })


def getConfigurationElementPage(request, id):
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
        print('Конфигурация с таким id не найдена')
        return redirect('configuration_elements')

    if configuration.status == 'deleted':
        return redirect('configuration_elements')

    # Получаем самолеты, связанные с данной конфигурацией
    elements = ConfigurationMap.objects.filter(configuration=configuration)

    if not elements.exists():
        print('Самолет для данной конфигурации не найден')
        return redirect('configuration_elements')

    # Получаем элементы конфигурации по идентификаторам и добавляем количество
    config_elements = ConfigurationElement.objects.filter(
        id__in=elements.values_list('element_id', flat=True)
    ).annotate(count=F('configurationmap__count'))

    return render(request, 'configuration.html', {
        'configuration_id': configuration.id,
        'customer_name': configuration.customer_name,
        'customer_phone': configuration.customer_phone,
        'customer_email': configuration.customer_email,
        'configuration_amount': calculate_configuration_total(configuration.id),
        'plane': configuration.plane,
        'config_elements': config_elements
    })



def deleteConfiguration(request, id):
    if request.method == 'POST':
        # Подсчитываем сумму конфигурации перед удалением
        total_price = calculate_configuration_total(id)
        
        # Обновляем статус конфигурации на удаленный
        with connection.cursor() as cursor:
            cursor.execute("UPDATE configurations SET status = 'deleted', total_price = %s WHERE id = %s", [total_price, id])
            print(f"Конфигурация удалена. Общая сумма: {total_price}")
        
        return redirect('configuration_elements')
    else:
        return Http404('Метод не поддерживается')



def addConfigurationElement(request, element_id):
    current_configuration_id = request.session.get('current_configuration_id')

    if not current_configuration_id:
        # Если заявки еще нет, создаем новую
        configuration = Configuration.objects.create(
            status='draft',
            customer_name='Guest',
            customer_phone='+123456789',
            customer_email='a@a.a'
        )
        request.session['current_configuration_id'] = configuration.id
    else:
        # Ищем текущую заявку
        configuration = Configuration.objects.filter(id=current_configuration_id, status='draft').first()

        # Если текущей заявки нет, создаем новую (на случай, если черновик был удален)
        if not configuration:
            configuration = Configuration.objects.create(
                status='draft',
                customer_name='Guest',
                customer_phone='+123456789',
                customer_email='a@a.a'
            )
            request.session['current_configuration_id'] = configuration.id

    # Проверяем, есть ли уже этот элемент в заявке
    existing_element = ConfigurationMap.objects.filter(configuration_id=configuration.id, element_id=element_id).exists()

    if existing_element:
        print('Этот элемент уже добавлен в конфигурацию')
        return redirect('configuration_elements')

    # Получаем элемент, который нужно добавить
    try:
        element = ConfigurationElement.objects.get(id=element_id)
    except ConfigurationElement.DoesNotExist:
        return redirect('configuration_elements')

    # Добавляем элемент в таблицу ConfigurationMap
    ConfigurationMap.objects.create(configuration_id=configuration.id, element_id=element.id, count=1)

    return redirect('configuration_elements')


def calculate_configuration_total(configuration_id):
    # Получаем все самолеты, связанные с данной конфигурацией
    elements = ConfigurationMap.objects.filter(configuration_id=configuration_id)
    
    total_sum = 60000000

    # Суммируем цены элементов конфигурации
    for el in elements:
        element = ConfigurationElement.objects.get(id=el.element_id)
        total_sum += element.price

    return total_sum
