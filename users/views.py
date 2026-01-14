from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TravelPreference
from .serializers import UserSerializer

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, get_user_model, login, logout 

# Create your views here.
class RegisterView(APIView) :
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        login(request, user)

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


User = get_user_model()

class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Thiếu email hoặc mật khẩu"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("Email hoặc mật khẩu không đúng")

        user = authenticate(
            username=user_obj.email,   # KEY POINT
            password=password
        )

        if user is None:
            raise AuthenticationFailed("Email hoặc mật khẩu không đúng")
        
        login(request, user)

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
        }, status=status.HTTP_200_OK)

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    refresh_token = request.data["refresh"]
    token = RefreshToken(refresh_token)
    token.blacklist()