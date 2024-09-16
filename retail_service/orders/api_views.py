from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
from .serializers import UserSerializer, ProductSerializer, OrderSerializer, ContactSerializer
from .models import Product, Order, Contact, ProductInfo, OrderItem, User, Shop
from .tasks import send_welcome_email, send_order_confirmation_email, process_order


# Вход пользователя
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            # Проверяем наличие email и пароля
            return Response({'Status': False, 'Error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, email=email, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({'Status': True, 'Token': token.key}, status=status.HTTP_200_OK)
        else:
            # Неверные учетные данные
            return Response({'Status': False, 'Error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# Регистрация пользователя
class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            send_welcome_email.delay(user.email)
            response = {
                'Status': True,
                'Token': token.key
            }
            return Response(response, status=status.HTTP_201_CREATED)
        # Ошибки валидации сериализатора
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# Выход пользователя
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
            # Успешный выход из системы
            return Response({"Status": True, "Detail": "You have been logged out"}, status=status.HTTP_200_OK)
        except:
            # Не удалось удалить токен
            return Response({'Status': False, 'Error': 'Something went wrong'}, status=status.HTTP_400_BAD_REQUEST)

# Список продуктов с фильтрацией и поиском
class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]  # Требует аутентификации
    authentication_classes = [TokenAuthentication]  # Аутентификация через токен
    filter_backends = [DjangoFilterBackend, SearchFilter]
    
    # Поля для фильтрации
    filterset_fields = ['product_infos__shop', 'category']
    
    # Поля для поиска
    search_fields = ['name', 'product_infos__name']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Дополнительная фильтрация, если требуется
        shop_id = self.request.query_params.get('shop_id')
        category_id = self.request.query_params.get('category_id')
        
        if shop_id:
            queryset = queryset.filter(product_infos__shop_id=shop_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset

# Работа с корзиной
class CartView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        cart = Order.objects.filter(user=request.user, status='basket').first()
        if cart:
            serializer = OrderSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Корзина пуста
        return Response({'Status': False, 'Error': 'Cart is empty'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        items = request.data.get('items')

        if not items:
            # Необходимо указать товары для добавления
            return Response({'Status': False, 'Error': 'You must specify items to add'}, status=status.HTTP_400_BAD_REQUEST)

        cart, created = Order.objects.get_or_create(user=request.user, status='basket')

        for index, item in enumerate(items):

            if not isinstance(item, dict):
                # Неверный формат данных для товара
                return Response({'Status': False, 'Error': f'Invalid data format for item {index}'}, status=status.HTTP_400_BAD_REQUEST)

            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)

            if not product_id:
                continue  # Или вернуть ошибку

            try:
                product_info = ProductInfo.objects.get(id=product_id)
                OrderItem.objects.create(order=cart, product=product_info, quantity=quantity)
            except ProductInfo.DoesNotExist:
                continue

        # Успешное добавление товаров в корзину
        return Response({'Status': True}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        # Получаем строку с идентификаторами через запятую
        product_ids = request.data.get('product_ids')
        if not product_ids:
            # Необходимо указать товары для удаления
            return Response({'Status': False, 'Error': 'You must specify items to delete'}, status=400)

        # Преобразуем строку в список идентификаторов
        try:
            product_ids = [int(pid.strip()) for pid in product_ids.split(',')]
        except ValueError:
            # Некорректный формат идентификаторов
            return Response({'Status': False, 'Error': 'Invalid format for identifiers'}, status=400)

        # Находим корзину пользователя
        cart = Order.objects.filter(user=request.user, status='basket').first()
        if not cart:
            # Корзина пуста
            return Response({'Status': False, 'Error': 'Cart is empty'}, status=400)

        # Удаляем товары из корзины
        deleted_items = cart.ordered_items.filter(product_id__in=product_ids).delete()

        if deleted_items[0] > 0:
            # Успешное удаление товаров из корзины
            return Response({'Status': True, 'Message': f'{deleted_items[0]} items removed from cart'}, status=204)
        else:
            # Товары не найдены в корзине
            return Response({'Status': False, 'Error': 'Items not found in cart'}, status=400)

# Работа с контактами
class ContactView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            # Успешное создание контакта
            return Response({'Status': True, 'Contact': serializer.data}, status=status.HTTP_201_CREATED)
        # Ошибки валидации сериализатора
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        contact_id = request.data.get('id')
        if not contact_id:
            # Необходимо указать ID контакта для удаления
            return Response({'Status': False, 'Error': 'You must specify the contact ID to delete'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            contact = Contact.objects.get(id=contact_id, user=request.user)
            contact.delete()
            # Успешное удаление контакта
            return Response({'Status': True}, status=status.HTTP_204_NO_CONTENT)
        except Contact.DoesNotExist:
            # Контакт не найден
            return Response({'Status': False, 'Error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)

# Подтверждение заказа
class OrderConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        order_id = request.data.get('order_id')
        contact_id = request.data.get('contact_id')

        if not order_id or not contact_id:
            # Необходимо указать order_id и contact_id
            return Response({'Status': False, 'Error': 'You must specify order_id and contact_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id, user=request.user, status='basket')
            contact = Contact.objects.get(id=contact_id, user=request.user)
            order.status = 'new'
            order.contact = contact
            order.save()
            
            # Вызов задач Celery для отправки email и обработки заказа
            send_order_confirmation_email.delay(order_id)
            process_order.delay(order_id)
            
            # Успешное подтверждение заказа
            return Response({'Status': True}, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            # Заказ не найден
            return Response({'Status': False, 'Error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        except Contact.DoesNotExist:
            # Контакт не найден
            return Response({'Status': False, 'Error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)

# История заказов
class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        # Получаем все заказы пользователя, кроме корзины
        return Order.objects.filter(user=self.request.user).exclude(status='basket')
