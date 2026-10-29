from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView


class MeView(APIView):
    """Devolve o utilizador autenticado. A SPA chama-a logo depois do login."""
    permission_classes = [IsAuthenticated]

    # Descreve a resposta para o Swagger (sem isto, o check dá o aviso drf_spectacular.W002).
    @extend_schema(responses=inline_serializer(
        name="Me",
        fields={
            "id": serializers.IntegerField(),
            "username": serializers.CharField(),
            "groups": serializers.ListField(child=serializers.CharField()),
        },
    ))
    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "groups": list(user.groups.values_list("name", flat=True)),
        })


class ThrottledTokenView(TokenObtainPairView):
    """POST /api/v1/auth/token/ com limite de tentativas.

    O scope 'auth' está definido em REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    (10 por minuto por IP). A 11.ª tentativa recebe 429 Too Many Requests,
    mesmo com a password certa — trava ataques de força bruta sem bloquear contas.
    """
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"