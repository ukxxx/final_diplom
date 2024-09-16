from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views
from .views import SocialAuthView


urlpatterns = [
    path('auth/<str:provider>/', SocialAuthView.as_view(), name='social-auth'),
    path('login/', api_views.LoginView.as_view(), name='login'),
    path('register/', api_views.RegisterView.as_view(), name='register'),
    path('logout/', api_views.LogoutView.as_view(), name='logout'),
    path('products/', api_views.ProductListView.as_view(), name='product-list'),
    path('cart/', api_views.CartView.as_view(), name='cart'),
    path('contacts/', api_views.ContactView.as_view(), name='contacts'),
    path('confirm-order/', api_views.OrderConfirmView.as_view(), name='confirm-order'),
    path('orders/', api_views.OrderListView.as_view(), name='order-list'),
]