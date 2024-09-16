from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.filters import SearchFilter
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate
from .serializers import UserSerializer, ProductSerializer, OrderSerializer, ContactSerializer
from .models import Product, Order, Contact, ProductInfo, OrderItem, User, Shop
from .tasks import send_welcome_email, send_order_confirmation_email, process_order


# Вход пользователя
class LoginView(APIView):
    """
    Вход пользователя в систему.

    Позволяет пользователю войти в систему, предоставляя email и пароль.
    Возвращает токен аутентификации при успешном входе.
    """

    def post(self, request):
        """
        Обработка POST-запроса для входа пользователя.

        **Параметры запроса:**
        - `email` (str): Электронная почта пользователя.
        - `password` (str): Пароль пользователя.

        **Ответы:**
        - `200 OK`: Успешный вход, возвращает токен.
        - `400 Bad Request`: Отсутствуют email или пароль.
        - `401 Unauthorized`: Неверные учетные данные.
        """
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
    """
    Регистрация нового пользователя.

    Позволяет новому пользователю зарегистрироваться, создавая учетную запись и возвращая токен аутентификации.
    Отправляет приветственное письмо после успешной регистрации.
    """

    def post(self, request):
        """
        Обработка POST-запроса для регистрации пользователя.

        **Параметры запроса:**
        - `email` (str): Электронная почта пользователя.
        - `password` (str): Пароль пользователя.
        - `username` (str): Имя пользователя.
        -  Другие поля, если есть.

        **Ответы:**
        - `201 Created`: Успешная регистрация, возвращает токен.
        - `400 Bad Request`: Ошибки валидации данных.
        """
        throttle_classes = AnonRateThrottle
        throttle_scope = 'register'
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
    """
    Выход пользователя из системы.

    Позволяет аутентифицированному пользователю выйти из системы, удаляя его токен аутентификации.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Обработка POST-запроса для выхода пользователя.

        **Ответы:**
        - `200 OK`: Успешный выход из системы.
        - `401 Unauthorized`: Отсутствие токена аутентификации.
        - `400 Bad Request`: Не удалось удалить токен.
        """
        try:
            request.user.auth_token.delete()
            # Успешный выход из системы
            return Response({"Status": True, "Detail": "You have been logged out"}, status=status.HTTP_200_OK)
        except:
            # Не удалось удалить токен
            return Response({'Status': False, 'Error': 'Something went wrong'}, status=status.HTTP_400_BAD_REQUEST)


# Список продуктов с фильтрацией и поиском
class ProductListView(generics.ListAPIView):
    """
    Список доступных продуктов.

    Позволяет просматривать список продуктов с возможностью фильтрации по магазинам и категориям,
    а также осуществлять поиск по названию продукта и имени магазина.
    """

    throttle_classes = [UserRateThrottle]
    throttle_scope = 'products'

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
        """
        Получение и дополнительная фильтрация набора запросов.

        **Дополнительная фильтрация:**
        - `shop_id` (int): ID магазина для фильтрации продуктов.
        - `category_id` (int): ID категории для фильтрации продуктов.

        **Возвращает:**
        - Отфильтрованный набор продуктов.
        """
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
    """
    Управление корзиной пользователя.

    Позволяет пользователю просматривать содержимое корзины, добавлять товары и удалять их.
    """
    
    throttle_classes = [UserRateThrottle]
    throttle_scope = 'cart'

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """
        Получение содержимого корзины.

        **Ответы:**
        - `200 OK`: Возвращает данные корзины.
        - `404 Not Found`: Корзина пуста.
        """
        cart = Order.objects.filter(user=request.user, status='basket').first()
        if cart:
            serializer = OrderSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Корзина пуста
        return Response({'Status': False, 'Error': 'Cart is empty'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        """
        Добавление товаров в корзину.

        **Параметры запроса:**
        - `items` (list): Список товаров для добавления. Каждый элемент должен содержать `product_id` и `quantity`.

        **Ответы:**
        - `201 Created`: Успешное добавление товаров.
        - `400 Bad Request`: Отсутствуют товары или неверный формат данных.
        """
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
        """
        Удаление товаров из корзины.

        **Параметры запроса:**
        - `product_ids` (str): Строка с идентификаторами товаров, разделёнными запятыми.

        **Ответы:**
        - `204 No Content`: Успешное удаление товаров.
        - `400 Bad Request`: Отсутствуют идентификаторы или неверный формат.
        """
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
    """
    Управление контактами пользователя.

    Позволяет пользователю просматривать, добавлять и удалять контактные данные.
    """
    
    throttle_classes = [UserRateThrottle]
    throttle_scope = 'contacts'

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ContactSerializer

    def get(self, request):
        """
        Получение списка контактов пользователя.

        **Ответы:**
        - `200 OK`: Возвращает список контактов.
        """
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Добавление нового контакта.

        **Параметры запроса:**
        - `name` (str): Имя контакта.
        - `phone` (str): Телефонный номер контакта.
        -  Другие поля, пристутствующие в модели Контакта.


        **Ответы:**
        - `201 Created`: Успешное создание контакта.
        - `400 Bad Request`: Ошибки валидации данных.
        """
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            # Успешное создание контакта
            return Response({'Status': True, 'Contact': serializer.data}, status=status.HTTP_201_CREATED)
        # Ошибки валидации сериализатора
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        Удаление контакта пользователя.

        **Параметры запроса:**
        - `id` (int): Идентификатор контакта для удаления.

        **Ответы:**
        - `204 No Content`: Успешное удаление контакта.
        - `400 Bad Request`: Отсутствует идентификатор контакта.
        - `404 Not Found`: Контакт не найден.
        """
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
    """
    Подтверждение заказа пользователя.

    Позволяет пользователю подтвердить заказ, указывая контактные данные.
    При подтверждении заказа изменяет статус заказа и запускает асинхронные задачи.
    """
    
    throttle_classes = [UserRateThrottle]
    throttle_scope = 'orders'

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        """
        Обработка POST-запроса для подтверждения заказа.

        **Параметры запроса:**
        - `order_id` (int): Идентификатор заказа.
        - `contact_id` (int): Идентификатор контактных данных.

        **Ответы:**
        - `200 OK`: Успешное подтверждение заказа.
        - `400 Bad Request`: Отсутствуют `order_id` или `contact_id`.
        - `404 Not Found`: Заказ или контакт не найдены.
        """
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
    """
    Просмотр истории заказов пользователя.

    Позволяет пользователю просматривать все свои заказы, исключая корзину.
    """
    
    throttle_classes = [UserRateThrottle]
    throttle_scope = 'orders'

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        """
        Получение набора запросов для истории заказов.

        **Возвращает:**
        - Все заказы пользователя, кроме тех, у которых статус 'basket'.
        """
        # Получаем все заказы пользователя, кроме корзины
        return Order.objects.filter(user=self.request.user).exclude(status='basket')
