from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, TravelPreference
from .serializers import UserSerializer
from django.contrib.auth import login

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# Create your views here.
class RegisterView(APIView) :
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Tạo token
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            },
            "message": "Đăng ký thành công, vui lòng chọn sở thích du lịch"
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView) :
    def post(self, request):
        email = request.data.get("email", None)
        user = get_object_or_404(User, email=email)

        password = request.data.get("password", None)
        is_check = user.check_password(password)

        if not is_check :
            raise AuthenticationFailed("Sai mật khẩu")
        
        login(request, user)

        refresh = RefreshToken.for_user(user)
        #
        return Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_preferences(request):
    # Nếu request.user là TokenUser, lấy User thật từ DB
    if hasattr(request.user, 'id'):
        user = User.objects.get(id=request.user.id)
    else:
        return Response({"error": "User not found"}, status=404)

    # Xóa sở thích cũ
    TravelPreference.objects.filter(user=user).delete()

    travel_types = request.data.get("travelTypes", [])
    locations = request.data.get("locations", [])

    # Tạo tổ hợp loại hình + địa điểm
    for t in travel_types:
        for loc in locations:
            TravelPreference.objects.create(
                user=user,
                travel_type=t,
                location=loc
            )

    return Response({"detail": "Preferences saved"})

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_preferences(request):
#     print("request.user:", request.user, type(request.user))
#     try:
#         user = User.objects.get(id=request.user.id)
#     except User.DoesNotExist:
#         return Response({"error": "User not found"}, status=404)
#
#     prefs = TravelPreference.objects.filter(user=user)
#     travel_types = list(set(p.travel_type for p in prefs))
#     locations = list(set(p.location for p in prefs))
#     return Response({
#         "travelTypes": travel_types,
#         "locations": locations
#     })