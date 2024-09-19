from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Product
from .tasks import generate_avatar_thumbnail, generate_product_image_thumbnail

@receiver(post_save, sender=User)
def trigger_avatar_thumbnail(sender, instance, **kwargs):
    if instance.avatar:
        generate_avatar_thumbnail.delay(instance.id)

@receiver(post_save, sender=Product)
def trigger_product_image_thumbnail(sender, instance, **kwargs):
    if instance.image:
        generate_product_image_thumbnail.delay(instance.id)