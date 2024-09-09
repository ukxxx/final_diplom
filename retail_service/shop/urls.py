from django.urls import path
from .importer import PartnerUpdate

urlpatterns = [
    path('api/update-partner/', PartnerUpdate.as_view(), name='update-partner'),
]