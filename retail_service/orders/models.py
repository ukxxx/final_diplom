from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission, AbstractBaseUser
from django_rest_passwordreset.tokens import get_token_generator

# Выбор состояний заказа
STATE_CHOICES = (
    ('basket', 'Basket status'),
    ('new', 'New'),
    ('confirmed', 'Confirmed'),
    ('assembled', 'Assembled'),
    ('sent', 'Sent'),
    ('delivered', 'Delivered'),
    ('canceled', 'Canceled'),
)

# Выбор типа пользователя
USER_TYPE_CHOICES = (
    ('shop', 'Shop'),
    ('buyer', 'Buyer'),
)

# Менеджер пользователей
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        # Создание пользователя с указанным email и паролем
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        # Создание обычного пользователя
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        # Создание суперпользователя
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        return self._create_user(email, password, **extra_fields)

# Кастомная модель пользователя
class User(AbstractUser):
    username = None  # Отключаем поле username
    email = models.EmailField('email address', unique=True)
    first_name = models.CharField('First name', max_length=30, blank=True)
    last_name = models.CharField('Last name', max_length=150, blank=True)
    company = models.CharField('Company', max_length=40, blank=True)
    position = models.CharField('Position', max_length=40, blank=True)
    type = models.CharField('User type', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'User list'
        ordering = ['email']


# Модель Магазин
class Shop(models.Model):
    name = models.CharField(max_length=50)
    url = models.URLField(null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

# Модель Категория
class Category(models.Model):
    name = models.CharField(max_length=40)
    shops = models.ManyToManyField(Shop, related_name='categories', blank=True)

    def __str__(self):
        return self.name

# Модель Продукт
class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name

# Модель Информация о продукте
class ProductInfo(models.Model):
    product = models.ForeignKey(Product, related_name='product_infos', on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='product_infos', on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2)
    external_id = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.product.name} from {self.shop.name}"

# Модель Параметр
class Parameter(models.Model):
    name = models.CharField(max_length=40)

    def __str__(self):
        return self.name

# Модель Значения параметров продукта
class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, related_name='product_parameters', on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, related_name='product_parameters', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"

# Модель Заказ
class Order(models.Model):
    user = models.ForeignKey(User, related_name='orders', on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=STATE_CHOICES, max_length=15)
    contact = models.ForeignKey('Contact', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.email}"

# Модель Элемент заказа
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='ordered_items', on_delete=models.CASCADE)
    product = models.ForeignKey(ProductInfo, related_name='ordered_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

# Модель Контакт
class Contact(models.Model):
    user = models.ForeignKey(User, related_name='contacts', on_delete=models.CASCADE)
    last_name = models.CharField(max_length=40)
    first_name = models.CharField(max_length=40)
    middle_name = models.CharField(max_length=40, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=40)
    street = models.CharField(max_length=100)
    house = models.CharField(max_length=10)
    building = models.CharField(max_length=10, blank=True)
    apartment = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"Contact: {self.first_name} {self.last_name}"

class ConfirmEmailToken(models.Model):
    """
    Model to store email confirmation tokens
    """
    user = models.ForeignKey(
        User, related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
        verbose_name=("User associated with the confirmation token")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=("Creation date"))
    key = models.CharField(("Key"), max_length=64, db_index=True, unique=True)

    @staticmethod
    def generate_key():
        """Generate a random token"""
        return get_token_generator().generate_token()

    def save(self, *args, **kwargs):
        # Сохранение токена, если его еще нет
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Confirmation token for user {self.user}"
