from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
import yaml
from yaml import Loader
from orders.models import Shop, Category, Product, ProductInfo, ProductParameter, Parameter
import requests

class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика через загрузку YAML-файла или указание URL
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request, *args, **kwargs):
        # Проверка, что пользователь является магазином
        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        # Получение файла или URL из запроса
        file = request.FILES.get('file')
        url = request.data.get('url')

        if not file and not url:
            return Response({'Status': False, 'Error': 'Необходимо загрузить YAML-файл или указать URL'}, status=400)

        if file:
            try:
                # Парсинг YAML-файла из загруженного файла
                data = yaml.load(file.read(), Loader=Loader)
            except yaml.YAMLError as e:
                return Response({'Status': False, 'Error': f'Ошибка в YAML файле: {str(e)}'}, status=400)
        elif url:
            try:
                # Загрузка файла по URL
                response = requests.get(url)
                response.raise_for_status()
                data = yaml.load(response.content, Loader=Loader)
            except requests.exceptions.RequestException as e:
                return Response({'Status': False, 'Error': f'Ошибка при загрузке файла по URL: {str(e)}'}, status=400)
            except yaml.YAMLError as e:
                return Response({'Status': False, 'Error': f'Ошибка в YAML файле: {str(e)}'}, status=400)

        # Проверка наличия ключей в данных
        required_keys = {'shop', 'categories', 'goods'}
        if not required_keys.issubset(data.keys()):
            return Response({'Status': False, 'Error': 'Отсутствуют необходимые ключи в YAML-файле'}, status=400)

        # Создание или получение магазина
        shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)

        # Добавление категорий
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
            category_object.shops.add(shop.id)
            category_object.save()

        # Удаление старой информации о продуктах для данного магазина
        ProductInfo.objects.filter(shop_id=shop.id).delete()

        # Добавление новых товаров
        for item in data['goods']:
            product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

            product_info = ProductInfo.objects.create(
                product=product,
                external_id=item['id'],
                name=item['model'],
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
                shop=shop
            )

            # Добавление параметров продукта
            for name, value in item['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter_object,
                    value=value
                )
                
        return Response({'Status': True})
