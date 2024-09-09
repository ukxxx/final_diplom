import requests
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from yaml import load, Loader
from orders.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter

class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if not url:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': str(e)}, status=400)

        response = requests.get(url)
        if response.status_code != 200:
            return JsonResponse({'Status': False, 'Error': 'Не удалось загрузить данные'}, status=400)

        data = load(response.content, Loader=Loader)
        shop, _ = Shop.objects.get_or_create(name=data['shop'], defaults={'user': request.user})
        
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], defaults={'name': category['name']})
            category_object.shops.add(shop)

        ProductInfo.objects.filter(shop=shop).delete()

        for item in data['goods']:
            product, _ = Product.objects.get_or_create(name=item['name'], defaults={'category_id': item['category']})
            product_info = ProductInfo.objects.create(
                product=product,
                shop=shop,
                name=item['model'],
                quantity=item['quantity'],
                price=item['price'],
                price_rrc=item['price_rrc']
            )

            for name, value in item['parameters'].items():
                parameter, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter,
                    value=value
                )

        return JsonResponse({'Status': True})
