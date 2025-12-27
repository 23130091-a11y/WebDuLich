from rest_framework import serializers
from .models import User, TravelPreference

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'avatar', 'username')

    def create(self, validated_data):
        password = validated_data.pop('password')
        # Lấy username từ validated_data trực tiếp
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelPreference
        fields = ['travel_type', 'location']