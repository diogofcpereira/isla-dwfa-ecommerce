from django.utils import timezone
from rest_framework import serializers

from .models import TestDrive


class TestDriveSerializer(serializers.ModelSerializer):
    car_name = serializers.CharField(source="car.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TestDrive
        fields = [
            "id",
            "car",
            "car_name",
            "customer",
            "scheduled_for",
            "status",
            "status_display",
            "notes",
            "created_at",
        ]
        # O cliente vem do login; o estado só muda em /confirm/, /decline/ e /cancel/.
        read_only_fields = ["customer", "status", "created_at"]
        # M2 (correção): sem isto, o DRF gera um UniqueTogetherValidator a partir da
        # uq_testdrive_car_slot_active, que corre ANTES do validate() e responde em inglês e
        # sem campo ("The fields car, scheduled_for must make a unique set."). A regra do
        # horário fica no validate(), com a mensagem no campo scheduled_for.
        validators = []

    def validate_car(self, car):
        if not car.is_active:
            raise serializers.ValidationError("Esta viatura já não está à venda.")
        return car

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("O test drive tem de ser marcado para o futuro.")
        if value.minute or value.second or value.microsecond:
            raise serializers.ValidationError("Os horários são de hora a hora (ex.: 10:00).")
        return value

    def validate(self, attrs):
        busy = TestDrive.objects.filter(
            car=attrs["car"], scheduled_for=attrs["scheduled_for"], status__in=TestDrive.ACTIVE
        ).exists()
        if busy:
            raise serializers.ValidationError(
                {"scheduled_for": "Este horário já está marcado para esta viatura."}
            )
        return attrs