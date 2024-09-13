from rest_framework import serializers
from .models import User, Product, Order, OrderItem, Contact, ProductParameter, ProductInfo

# Сериализатор для модели User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'type']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_email(self, value):
        # Проверяем уникальность email
        user = self.context.get('request').user
        if User.objects.filter(email=value).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        # Используем менеджер create_user для создания пользователя
        user = User.objects.create_user(**validated_data)
        return user

# Сериализатор для параметров продукта
class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source='parameter.name')

    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']

# Сериализатор для информации о продукте
class ProductInfoSerializer(serializers.ModelSerializer):
    shop = serializers.CharField(source='shop.name')
    characteristics = ProductParameterSerializer(source='product_parameters', many=True)

    class Meta:
        model = ProductInfo
        fields = ['id', 'name', 'price', 'price_rrc', 'quantity', 'shop', 'characteristics']

# Сериализатор для продуктов
class ProductSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    product_infos = ProductInfoSerializer(many=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'product_infos']

# Сериализатор для товаров в заказе
class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(source='product')

    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'quantity']

# Сериализатор для заказов
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='ordered_items', many=True)
    total_sum = serializers.SerializerMethodField()
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = Order
        fields = ['id', 'dt', 'status', 'items', 'total_sum']

    def get_total_sum(self, obj):
        # Вычисляем общую сумму заказа
        return sum(item.quantity * item.product.price_rrc for item in obj.ordered_items.all())

# Сериализатор для контактов
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'last_name', 'first_name', 'middle_name', 'email', 'phone', 'city', 'street', 'house', 'building', 'apartment']
