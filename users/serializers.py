from rest_framework import serializers
from .models import User, TravelPreference

class UserSerializer(serializers.ModelSerializer) :
    #
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'avatar') #

    def create(self, validated_data):
        # Tự tạo username nếu không có
        username = validated_data.get('username') or validated_data['email'].split('@')[0]

        user = User(
            email=validated_data['email'],
            username=username,
            avatar=validated_data.get('avatar')
        )
        user.set_password(validated_data['password'])  # hash password
        user.save()
        return user

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelPreference
        fields = ['travel_type', 'location']