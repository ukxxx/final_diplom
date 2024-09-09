from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from .serializers import UserSerializer, ProductSerializer, OrderSerializer, ContactSerializer
from .models import Product, Order, Contact, User

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                login(request, user)
                return Response({'Status': True}, status=status.HTTP_200_OK)
            else:
                return Response({'Status': False, 'Error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'Status': False, 'Error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'Status': True}, status=status.HTTP_201_CREATED)
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = Order.objects.filter(user=request.user, status='basket').first()
        if cart:
            serializer = OrderSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'Status': False, 'Error': 'Cart is empty'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity'))
        product = Product.objects.get(id=product_id)
        order, _ = Order.objects.get_or_create(user=request.user, status='basket')
        order.products.add(product, through_defaults={'quantity': quantity})
        return Response({'Status': True}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        product_id = request.data.get('product_id')
        order = Order.objects.filter(user=request.user, status='basket').first()
        order.products.filter(id=product_id).delete()
        return Response({'Status': True}, status=status.HTTP_204_NO_CONTENT)

class ContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class OrderConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        contact_id = request.data.get('contact_id')
        order = Order.objects.get(id=order_id, user=request.user)
        contact = Contact.objects.get(id=contact_id, user=request.user)
        order.status = 'confirmed'
        order.contact = contact
        order.save()
        return Response({'Status': True}, status=status.HTTP_200_OK)

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(status='basket')