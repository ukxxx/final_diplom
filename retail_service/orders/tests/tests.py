from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from unittest.mock import patch
from ..models import Product, ProductInfo, Shop, Order, OrderItem, Contact

User = get_user_model()

# Тесты для LoginView
class LoginViewTest(APITestCase):
    def setUp(self):
        self.login_url = reverse('login')
        self.user = User.objects.create_user(email='testuser@example.com', password='testpassword123')

    def test_login_success(self):
        data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Token', response.data)

    def test_login_failure_wrong_password(self):
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Error', response.data)

    def test_login_failure_missing_fields(self):
        data = {
            'email': 'testuser@example.com'
            # Отсутствует пароль
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Error', response.data)

# Тесты для RegisterView
class RegisterViewTest(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')

    @patch('orders.tasks.send_welcome_email.delay')
    def test_register_success(self, mock_send_welcome_email_delay):
        data = {
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+1234567890'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('Token', response.data)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())
        mock_send_welcome_email_delay.assert_called_once()

    def test_register_failure_existing_email(self):
        User.objects.create_user(email='existing@example.com', password='password123')
        data = {
            'email': 'existing@example.com',
            'password': 'newpassword123',
            'username': 'newuser'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)

    def test_register_failure_missing_fields(self):
        data = {
            'email': 'incomplete@example.com'
            # Отсутствуют пароль и другие поля
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Errors', response.data)

# Тесты для LogoutView
class LogoutViewTest(APITestCase):
    def setUp(self):
        self.logout_url = reverse('logout')
        self.user = User.objects.create_user(email='logoutuser@example.com', password='logoutpassword123')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_logout_success(self):
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_failure_no_token(self):
        self.client.credentials()  # Удаляем токен
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

# Тесты для CartView
class CartViewTest(APITestCase):
    def setUp(self):
        self.cart_url = reverse('cart')
        self.user = User.objects.create_user(email='cartuser@example.com', password='cartpassword123')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Создаём продукт и магазин
        self.shop = Shop.objects.create(name='Test Shop')
        self.product = Product.objects.create(name='Test Product', category='Test Category')
        self.product_info = ProductInfo.objects.create(product=self.product, shop=self.shop)

    def test_get_empty_cart(self):
        response = self.client.get(self.cart_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Error', response.data)

    def test_add_items_to_cart(self):
        data = {
            'items': [
                {'product_id': self.product_info.id, 'quantity': 2}
            ]
        }
        response = self.client.post(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cart = Order.objects.get(user=self.user, status='basket')
        self.assertEqual(cart.ordered_items.count(), 1)
        self.assertEqual(cart.ordered_items.first().quantity, 2)

    def test_get_cart_with_items(self):
        cart = Order.objects.create(user=self.user, status='basket')
        OrderItem.objects.create(order=cart, product=self.product_info, quantity=3)
        response = self.client.get(self.cart_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ordered_items'][0]['quantity'], 3)

    def test_delete_items_from_cart(self):
        cart = Order.objects.create(user=self.user, status='basket')
        OrderItem.objects.create(order=cart, product=self.product_info, quantity=3)
        data = {
            'product_ids': f'{self.product_info.id}'
        }
        response = self.client.delete(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(cart.ordered_items.count(), 0)

    def test_delete_nonexistent_item(self):
        cart = Order.objects.create(user=self.user, status='basket')
        OrderItem.objects.create(order=cart, product=self.product_info, quantity=3)
        data = {
            'product_ids': '999'  # Некорректный ID
        }
        response = self.client.delete(self.cart_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Error', response.data)

# Тесты для OrderConfirmView
class OrderConfirmViewTest(APITestCase):
    def setUp(self):
        self.confirm_order_url = reverse('order_confirm')
        self.user = User.objects.create_user(email='orderuser@example.com', password='orderpassword123')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Создаём продукт и магазин
        self.shop = Shop.objects.create(name='Test Shop')
        self.product = Product.objects.create(name='Test Product', category='Test Category')
        self.product_info = ProductInfo.objects.create(product=self.product, shop=self.shop)

        # Создаём корзину и добавляем товар
        self.cart = Order.objects.create(user=self.user, status='basket')
        self.order_item = OrderItem.objects.create(order=self.cart, product=self.product_info, quantity=2)

        # Создаём контакт
        self.contact = Contact.objects.create(user=self.user, name='Test Contact', phone='1234567890')

    @patch('orders.tasks.send_order_confirmation_email.delay')
    @patch('orders.tasks.process_order.delay')
    def test_order_confirm_success(self, mock_process_order_delay, mock_send_order_confirmation_email_delay):
        data = {
            'order_id': self.cart.id,
            'contact_id': self.contact.id
        }
        response = self.client.post(self.confirm_order_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_order = Order.objects.get(id=self.cart.id)
        self.assertEqual(updated_order.status, 'new')
        self.assertEqual(updated_order.contact, self.contact)
        mock_send_order_confirmation_email_delay.assert_called_once_with(self.cart.id)
        mock_process_order_delay.assert_called_once_with(self.cart.id)

    def test_order_confirm_failure_invalid_order(self):
        data = {
            'order_id': 999,  # Некорректный ID заказа
            'contact_id': self.contact.id
        }
        response = self.client.post(self.confirm_order_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Error', response.data)

    def test_order_confirm_failure_invalid_contact(self):
        data = {
            'order_id': self.cart.id,
            'contact_id': 999  # Некорректный ID контакта
        }
        response = self.client.post(self.confirm_order_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Error', response.data)

    def test_order_confirm_failure_missing_fields(self):
        data = {
            'order_id': self.cart.id
            # Отсутствует contact_id
        }
        response = self.client.post(self.confirm_order_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Error', response.data)

# Тесты для OrderListView
class OrderListViewTest(APITestCase):
    def setUp(self):
        self.order_list_url = reverse('orders')
        self.user = User.objects.create_user(email='orderlistuser@example.com', password='orderlistpassword123')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Создаём магазин и продукты
        self.shop = Shop.objects.create(name='Shop List')
        self.product = Product.objects.create(name='Order Product', category='Order Category')
        self.product_info = ProductInfo.objects.create(product=self.product, shop=self.shop)

        # Создаём заказы
        self.order1 = Order.objects.create(user=self.user, status='new', contact=None)
        self.order2 = Order.objects.create(user=self.user, status='completed', contact=None)
        OrderItem.objects.create(order=self.order1, product=self.product_info, quantity=1)
        OrderItem.objects.create(order=self.order2, product=self.product_info, quantity=2)

    def test_get_order_list(self):
        response = self.client.get(self.order_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_order_list_excludes_basket(self):
        basket_order = Order.objects.create(user=self.user, status='basket')
        response = self.client.get(self.order_list_url, format='json')
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_access(self):
        self.client.credentials()  # Удаляем токен
        response = self.client.get(self.order_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
