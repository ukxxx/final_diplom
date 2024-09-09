from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from .views import ShopViewSet, CategoryViewSet, ProductViewSet, OrderViewSet, UserContactViewSet
from . import api_views

# router = DefaultRouter()
# router.register(r'stores', ShopViewSet)
# router.register(r'categories', CategoryViewSet)
# router.register(r'products', ProductViewSet)
# router.register(r'orders', OrderViewSet)
# router.register(r'usercontacts', UserContactViewSet)

urlpatterns = [
    # path('', include(router.urls)),
    path('login/', api_views.LoginView.as_view(), name='login'),
    path('register/', api_views.RegisterView.as_view(), name='register'),
    path('products/', api_views.ProductListView.as_view(), name='product-list'),
    path('cart/', api_views.CartView.as_view(), name='cart'),
    path('contacts/', api_views.ContactView.as_view(), name='contacts'),
    path('confirm-order/', api_views.OrderConfirmView.as_view(), name='confirm-order'),
    path('orders/', api_views.OrderListView.as_view(), name='order-list'),
]