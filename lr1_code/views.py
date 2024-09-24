from django.http import Http404
from django.shortcuts import render

configuration_elements = [
    {
        'id': 0,
        'name': 'Executive',
        'price': 24000000,
        'key_info': '18 пассажиров',
        'category': 'Компоновка салона',
        'image': 'http://127.0.0.1:9000/assets/0.png',
        'detail_text': 'В этой планировке предусмотрены четыре отдельные жилые зоны, каждая из которых предлагает комфорт и удобства для максимально продуктивных и расслабляющих перелетов. Первая зона — это передняя клубная каюта с просторными креслами, идеально подходящими для неформальных встреч и общения. Далее идет конференц-каюта со столом, рассчитанным на шесть человек, что позволяет проводить переговоры или деловые встречи прямо на борту. Развлекательная каюта включает удобный диван и сервант с телевизором с большим экраном, предоставляя отличные условия для отдыха и просмотра мультимедийного контента. Последняя зона — это каюта для отдыха, оборудованная диваном, клубным креслом и угловой тумбой с телевизором, где пассажиры могут расслабиться и насладиться тишиной. Самолет в данной планировке рассчитан максимум на 18 человек, обеспечивая каждому зону для отдыха и работы в непрерывных дальних перелетах.'
    },
    {
        'id': 1,
        'name': 'Contemporary',
        'price': 1000000,
        'key_info': 'Темные мебель и пол',
        'category': 'Дизайн салона',
        'image': 'http://127.0.0.1:9000/assets/1.jpeg',
        'detail_text': 'В салоне этой планировки преобладают темные материалы и элементы мебели, которые создают атмосферу современности и элегантности. Интерьер оформлен в строгих линиях с акцентом на минимализм и функциональность, что идеально подходит для деловых путешествий. Просторные кресла и диваны выполнены из темной кожи высокого качества, что придает интерьеру солидность и изысканность. Полы из темного дерева дополняют общую концепцию.  Такая планировка прекрасно сочетается с авионикой нового поколения, позволяя пассажирам наслаждаться максимальным комфортом во время перелетов на дальние расстояния, сохраняя деловой стиль.'
    },
    {
        'id': 2,
        'name': 'Garmin G3000',
        'price': 385000,
        'key_info': 'Сенсорные дисплеи, интеграция с автопилотом.',
        'category': 'Авионика',
        'image': 'http://127.0.0.1:9000/assets/2.png',
        'detail_text': 'Garmin G3000 — это инновационная авионика, которая обеспечивает передовые возможности управления полетом. Сенсорные дисплеи высокой четкости дают пилотам возможность эффективно контролировать все аспекты полета. Интеграция с автопилотом упрощает навигацию и маневрирование, делая полет максимально безопасным и комфортным.  Система включает в себя улучшенную навигацию и прогнозирование метеоусловий, что значительно снижает нагрузку на пилота во время сложных перелетов. Такая система подходит как для начинающих, так и для опытных пилотов, предоставляя интуитивное управление и надежную поддержку.'
    },
    {
        'id': 3,
        'name': 'Globetrotter',
        'price': 26000000,
        'key_info': '15 пассажиров',
        'category': 'Компоновка салона',
        'image': 'http://127.0.0.1:9000/assets/3.png',
        'detail_text': 'Globetrotter — это роскошная компоновка салона, которая создается для максимального комфорта и удобства при дальних перелетах. Внутреннее пространство самолета включает три уникальные зоны. Первая — это зал переговоров, где удобно проводить бизнес-встречи в неформальной обстановке. Вторая зона — это зона отдыха с удобными диванами и мягким освещением, где можно расслабиться и восстановить силы.  Третья зона включает спальные места с индивидуальными местами для сна. Общая вместимость салона — до 15 пассажиров, что позволяет создать уютную и спокойную атмосферу для длительных путешествий.'
    },
    {
        'id': 4,
        'name': 'Timeless',
        'price': 1400000,
        'key_info': 'Светлые мебель и пол',
        'category': 'Дизайн салона',
        'image': 'http://127.0.0.1:9000/assets/4.jpeg',
        'detail_text': 'Планировка Timeless воплощает в себе идею классической элегантности и светлого интерьера. В салоне преобладают светлые материалы, которые создают ощущение простора и легкости. Мебель выполнена в светлых тонах, что делает интерьер воздушным и современным. Светлые деревянные полы добавляют тепла и уюта, гармонично сочетаясь с мягкими креслами и диванами.  Данная планировка идеально подходит для тех, кто ценит классический дизайн с элементами модерна. Салон Timeless обеспечивает комфорт и роскошь, создавая приятную атмосферу для длительных перелетов, будь то деловая поездка или отдых.'
    },
    {
        'id': 5,
        'name': 'Garmin G5000',
        'price': 643000,
        'key_info': 'Расширенные сенсорные дисплеи, интеграция с дополнительными системами.',
        'category': 'Авионика',
        'image': 'http://127.0.0.1:9000/assets/5.png',
        'detail_text': 'Garmin G5000 представляет собой модернизированную версию системы авионики с расширенными возможностями. В системе используются более крупные сенсорные дисплеи с высоким разрешением, что обеспечивает еще большее удобство управления. Эта система идеально интегрируется с дополнительными системами безопасности и навигации, включая улучшенные функции автопилота и мониторинг состояния полета.  Garmin G5000 предоставляет пилотам удобный и интуитивный интерфейс, позволяющий оптимизировать процесс управления воздушным судном. Это одна из самых передовых систем авионики на рынке, обеспечивающая максимальную надежность и безопасность.'
    },
    {
        'id': 6,
        'name': 'General Electric Passport',
        'price': 6000000,
        'key_info': '18.000 фунтов тяги',
        'category': 'Двигатель',
        'image': 'http://127.0.0.1:9000/assets/6.png',
        'detail_text': 'Двигатель General Electric Passport предлагает невероятную мощность в 18.000 фунтов тяги, что делает его одним из лучших в своем классе для бизнес-джетов. Этот двигатель был разработан с учетом экономии топлива и снижения выбросов, что делает его идеальным выбором для дальних перелетов. Его высокоэффективная конструкция обеспечивает плавную и тихую работу, снижая уровень шума в салоне самолета.  General Electric Passport — это идеальное сочетание мощности и эффективности, что позволяет самолетам набирать высоту быстрее и преодолевать большие расстояния без необходимости дозаправки. Это решение для тех, кто ищет надежность и производительность.'
    },
    {
        'id': 7,
        'name': 'Rolls-Royce Pearl',
        'price': 5300000,
        'key_info': '15.000 фунтов тяги',
        'category': 'Двигатель',
        'image': 'http://127.0.0.1:9000/assets/7.png',
        'detail_text': 'Rolls-Royce Pearl — это новый уровень в мире авиационных двигателей, предоставляющий 15.000 фунтов тяги для бизнес-джетов. Этот двигатель разработан с учетом последних инноваций в аэрокосмической технологии, обеспечивая высокую топливную эффективность и уменьшенные выбросы. Rolls-Royce Pearl предлагает исключительную производительность, обеспечивая быстрый набор высоты и стабильный полет даже на максимальной дальности.  Благодаря своей тихой работе и низкому уровню вибраций, этот двигатель гарантирует комфортное путешествие для пассажиров и экипажа. Rolls-Royce Pearl — выбор для тех, кто ценит передовые технологии и премиальное качество.'
    }
]

configurations = [
    {
        'id': 0,
        'configuration_amount': 86000000,
        'customer_name': "Peter Brown",
        'customer_phone': '+79647938863',
        'customer_email': 'peterb@gmail.com',
        'configuration_elements': [3]
    }
]

plane = [
    {
        'id': 0,
        'plane': 'Global 7500',
        'element_id': 3,
        'configuration_id': 0
    }
]


def getStartPage(request):
    return render(request, 'start.html')

def getMainPage(request):
    category = request.GET.get('categories', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')

    filtered_items = configuration_elements
    
    if category:
        filtered_items = [item for item in filtered_items if item['category'] == category]
    
    if price_min:
        filtered_items = [item for item in filtered_items if float(item['price']) >= float(price_min)]
    
    if price_max:
        filtered_items = [item for item in filtered_items if float(item['price']) <= float(price_max)]

    # Получение идентификатора конфигурации из таблицы plane
    plane_id = plane[0]['configuration_id'] if plane else None
    
    if plane_id is not None:
        # Найти конфигурацию по идентификатору
        configuration = next((config for config in configurations if config['id'] == plane_id), None)
        if configuration:
            # Подсчет элементов конфигурации через plane
            configuration_elements_ids = [p['element_id'] for p in plane if p['configuration_id'] == plane_id]
            configuration_counter = len(configuration_elements_ids)
        else:
            configuration_counter = 0
    else:
        configuration_counter = 0

    return render(request, 'main.html', {
        'configuration_elements': filtered_items,
        'configuration_counter': configuration_counter,
        'selected_category': category,
        'selected_price_min': price_min,
        'selected_price_max': price_max
    })



def getDetailPage(request, id):
    item = next((item for item in configuration_elements if item['id'] == id), None)

    if not item:
        raise Http404('Элемент с таким id не найден')

    return render(request, 'detail.html', {
        'id': item['id'],
        'name': item['name'],
        'price': item['price'],
        'key_info': item['key_info'],
        'category': item['category'],
        'image': item['image'],
        'detail_text': item['detail_text']
    })

def getConfigurationPage(request, id):
    # Поиск конфигурации по id
    configuration = next((config for config in configurations if config['id'] == id), None)

    if not configuration:
        raise Http404('Конфигурация с таким id не найдена')

    # Получение элементов конфигурации из массива configuration_elements в конфигурации
    config_elements_ids = configuration['configuration_elements']

    # Получение элементов конфигурации по идентификаторам
    config_elements = [element for element in configuration_elements if element['id'] in config_elements_ids]

    return render(request, 'configuration.html', {
        'configuration_id': configuration['id'],
        'customer_name': configuration['customer_name'],
        'customer_phone': configuration['customer_phone'],
        'customer_email': configuration['customer_email'],
        'configuration_amount': configuration['configuration_amount'],
        'config_elements': config_elements
    })




