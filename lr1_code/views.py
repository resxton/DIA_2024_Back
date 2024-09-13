from django.shortcuts import render
from .models import ConfigurationElement, Configuration

configuration_elements = [
    {
        'id': 0,
        'name': 'Executive',
        'price': 24000000,
        'key_info': '18 пассажиров',
        'category': 'interior_layout',
        'image': 'floorplan-executive.png'
    },
    {
        'id': 1,
        'name': 'Contemporary',
        'price': 1000000,
        'key_info': 'Темные мебель и пол',
        'category': 'interior_design',
        'image': 'design-contemporary.jpeg'
    },
    {
        'id': 2,
        'name': 'Garmin G3000',
        'price': 385000,
        'key_info': 'Сенсорные дисплеи, интеграция с автопилотом.',
        'category': 'avionics',
        'image': 'avionics-g3000.png'
    },
    {
        'id': 3,
        'name': 'Globetrotter',
        'price': 26000000,
        'key_info': '15 пассажиров',
        'category': 'interior_layout',
        'image': 'floorplan-globetrotter.png'
    },
    {
        'id': 4,
        'name': 'Timeless',
        'price': 1400000,
        'key_info': 'Светлые мебель и пол',
        'category': 'interior_design',
        'image': 'design-timeless.jpeg'
    },
    {
        'id': 5,
        'name': 'Garmin G5000',
        'price': 643000,
        'key_info': 'Расширенные сенсорные дисплеи, интеграция с дополнительными системами.',
        'category': 'avionics',
        'image': 'avionics-g5000.png'
    },
    {
        'id': 6,
        'name': 'General Electric Passport',
        'price': 6000000,
        'key_info': '18.000 фунтов тяги',
        'category': 'engine',
        'image': 'engine-ge-passport.png'
    },
    {
        'id': 7,
        'name': 'Rolls-Royce Pearl',
        'price': 5300000,
        'key_info': '15.000 фунтов тяги',
        'category': 'engine',
        'image': 'engine-rr-pearl.png'
    }
]

configurations = [
    {
        'id': 0,
        'amount': 64000000,
        'customer_name': '',
        'customer_phone': '',
        'customer_email': '',
    }
]



CATEGORY_CHOICES = {
    'interior_layout': 'Компоновка салона',
    'interior_design': 'Дизайн салона',
    'avionics': 'Авионика',
    'engine': 'Двигатель'
}

def get_readable_category(category_code):
    return CATEGORY_CHOICES.get(category_code, category_code)

def getStartPage(request):
    return render(request, 'start.html')

def getMainPage(request):
    category = request.GET.get('categories', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')

    # Debug prints
    print(f"Selected Category: {category}")
    print(f"Price from: {price_min} to: {price_max}")

    filtered_items = configuration_elements
    
    if category:
        filtered_items = [item for item in filtered_items if item['category'] == category]
    
    if price_min:
        filtered_items = [item for item in filtered_items if float(item['price']) >= float(price_min)]
    
    if price_max:
        filtered_items = [item for item in filtered_items if float(item['price']) <= float(price_max)]

    return render(request, 'main.html', {
        'configuration_elements': filtered_items,
        'configuration_counter': len(filtered_items),
        'selected_category': category,
        'selected_price_min': price_min,
        'selected_price_max': price_max
    })

def getDetailPage(request):
    # You should provide a real implementation based on your detail view requirements
    return render(request, 'detail.html', {
        'name': "Executive",
        'type': "floorplan",
        'price': 24000000
    })

def getDetailPage(request, id):
    return render(request, 'detail.html', {
        'id': id,
        'name': 'Rolls-Royce Pearl',
        'price': 5300000,
        'key_info': '15.000 фунтов тяги',
        'category': 'engine',
        'image': 'engine-rr-pearl.png'
    })

def getConfigurationPage(request):
    return render(request, 'configuration.html', {
        'configuration_id': 1
    })


def detail(request):
    # Provide a real implementation here to show details of an item
    return render(request, 'detail.html', {
        'name': "Executive",
        'type': "floorplan",
        'price': 24000000
    })
