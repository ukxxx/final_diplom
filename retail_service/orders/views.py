from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from social_django.utils import load_strategy, load_backend
from social_core.exceptions import MissingBackend, AuthTokenError
from drf_spectacular.utils import extend_schema
from .serializers import UserSerializer

User = get_user_model()

class SocialAuthView(APIView):
    """
    Социальная аутентификация через Google и GitHub.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=None,
        responses={
            200: UserSerializer,
            400: {'error': 'Invalid data'},
            401: {'error': 'Authentication failed'},
        }
    )
    def post(self, request, provider):
        """
        Обработка POST-запроса для социальной аутентификации.

        **Параметры запроса:**
        - `access_token` (str): Токен доступа, полученный от социального провайдера.

        **Ответы:**
        - `200 OK`: Успешная аутентификация, возвращает пользователя и токен.
        - `400 Bad Request`: Неверные данные.
        - `401 Unauthorized`: Аутентификация не удалась.
        """

        access_token = request.data.get('access_token')
        if not access_token:
            return Response({'error': 'Access token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            strategy = load_strategy(request)
            backend = load_backend(strategy=strategy, name=provider, redirect_uri=None)
        except MissingBackend:
            return Response({'error': 'Invalid authentication provider'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = backend.do_auth(access_token)
        except AuthTokenError:
            return Response({'error': 'Authentication failed'}, status=status.HTTP_401_UNAUTHORIZED)

        if user and user.is_authenticated:
            token, created = Token.objects.get_or_create(user=user)
            serializer = UserSerializer(user)
            data = serializer.data
            data['token'] = token.key
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Authentication failed'}, status=status.HTTP_401_UNAUTHORIZED)
