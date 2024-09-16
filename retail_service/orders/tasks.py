from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Order



User = get_user_model()

@shared_task
def send_welcome_email(user_id):
    """
    Отправка приветственного email после регистрации пользователя.
    """
    try:
        user = User.objects.get(id=user_id)
        subject = "Welcome to Retail Service!"
        message = f"Hello, {user.username}! Thank you for registering with us."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        send_mail(subject, message, from_email, recipient_list)
        return f"Welcome email for user {user.username} was sent."
    except User.DoesNotExist:
        return f"User with ID {user_id} not found."
    except Exception as e:
        return f"Error when sending welcome email: {str(e)}"

@shared_task
def send_order_confirmation_email(order_id):
    """
    Отправка подтверждающего email пользователю после подтверждения заказа.
    """
    try:
        order = Order.objects.get(id=order_id)
        user = order.user
        subject = f"Confirmation of Order #{order.id}"
        message = f"Hello, {user.username}! Your order #{order.id} was confirmed."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        send_mail(subject, message, from_email, recipient_list)
        return f"Order confirmation email for order #{order.id} has been sent."
    except Order.DoesNotExist:
        return f"Order with ID {order_id} not found."
    except Exception as e:
        return f"Error when sending confirmation email: {str(e)}"

@shared_task
def process_order(order_id):
    """
    Обработка заказа
    """
    try:
        order = Order.objects.get(id=order_id)
        return f"Order #{order.id} processed."
    except Order.DoesNotExist:
        return f"Order #{order_id} not found."
    except Exception as e:
        return f"Error during order processing: {str(e)}"
