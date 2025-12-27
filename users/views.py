from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, TravelPreference
from .serializers import UserSerializer

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import login # Import thêm

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
        password = request.data.get("password", None)

        user = User.objects.filter(email=email).first()

        if user and user.check_password(password):
            login(request, user) # <--- THÊM DÒNG NÀY để tạo Session cho trình duyệt

        if user is None or not user.check_password(password):
            raise AuthenticationFailed("Email hoặc mật khẩu không đúng")

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
            }
        })

#
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_preferences(request):
    user = request.user

    travel_types = request.data.get("travelTypes", [])
    locations = request.data.get("locations", [])

    if not travel_types or not locations:
        return Response(
            {"error": "Phải chọn ít nhất 1 loại hình và 1 địa điểm"},
            status=400
        )

    # Xóa cũ
    TravelPreference.objects.filter(user=user).delete()

    # Tạo mới (loại trùng)
    objs = [
        TravelPreference(
            user=user,
            travel_type=t.strip(),
            location=loc.strip()
        )
        for t in set(travel_types)
        for loc in set(locations)
    ]

    TravelPreference.objects.bulk_create(objs)

    return Response({"detail": "Preferences saved"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception:
        return Response({"error": "Invalid token"}, status=400)

    return Response({"message": "Logged out"})