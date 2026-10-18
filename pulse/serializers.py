from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import PriceAlert
User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    class Meta:
        model = User
        fields = ("username", "password", "email")
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        fields = ("id", "origin", "destination", "threshold_price", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")
    def validate_origin(self, value):
        value = value.strip().upper()
        if not value.isalpha():
            raise serializers.ValidationError("Origin must contain letters only.")
        return value
    def validate_destination(self, value):
        value = value.strip().upper()
        if not value.isalpha():
            raise serializers.ValidationError("Destination must contain letters only.")
        return value
    def validate(self, attrs):
        if attrs.get("origin") == attrs.get("destination"):
            raise serializers.ValidationError("Origin and destination must be different.")
        if attrs.get("threshold_price", 0) <= 0:
            raise serializers.ValidationError({"threshold_price": "Must be greater than zero."})
        return attrs
