"""
Unit tests cho Users app
Test coverage cho authentication, registration, preferences
"""
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import User, TravelPreference


class UserModelTest(TestCase):
    """Test User model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_creation(self):
        """Test tạo user"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))
    
    def test_user_str(self):
        """Test __str__ method"""
        # User model uses email as __str__
        self.assertEqual(str(self.user), 'test@example.com')


class TravelPreferenceModelTest(TestCase):
    """Test TravelPreference model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.preference = TravelPreference.objects.create(
            user=self.user,
            travel_type='Biển',
            location='Quảng Ninh'
        )
    
    def test_preference_creation(self):
        """Test tạo travel preference"""
        self.assertEqual(self.preference.travel_type, 'Biển')
        self.assertEqual(self.preference.location, 'Quảng Ninh')
        self.assertEqual(self.preference.user, self.user)
    
    def test_preference_relationship(self):
        """Test relationship với User"""
        preferences = TravelPreference.objects.filter(user=self.user)
        self.assertEqual(preferences.count(), 1)
        self.assertIn(self.preference, preferences)


class RegisterViewTest(TestCase):
    """Test registration view"""
    
    def setUp(self):
        self.client = APIClient()
        # Note: URLs don't have names, use direct path
        self.register_url = '/auth/register'
    
    def test_register_success(self):
        """Test đăng ký thành công"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'newpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        
        # Check user created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
    
    def test_register_duplicate_email(self):
        """Test đăng ký với email trùng"""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='pass123'
        )
        
        data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': 'newpass123',
            'password2': 'newpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_invalid_data(self):
        """Test đăng ký với data không hợp lệ"""
        data = {
            'username': '',
            'email': 'invalid-email',
            'password': '123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(TestCase):
    """Test login view"""
    
    def setUp(self):
        self.client = APIClient()
        # Note: URLs don't have names, use direct path
        self.login_url = '/auth/login'
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_success(self):
        """Test đăng nhập thành công"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
    
    def test_login_wrong_password(self):
        """Test đăng nhập với mật khẩu sai"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpass'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        # May return 401 or 403 depending on implementation
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_login_nonexistent_user(self):
        """Test đăng nhập với user không tồn tại"""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SavePreferencesTest(TestCase):
    """Test save preferences view"""
    
    def setUp(self):
        self.client = APIClient()
        self.preferences_url = reverse('save_preferences')
        
        # Create and authenticate user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Get token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
    
    def test_save_preferences_authenticated(self):
        """Test lưu preferences khi đã đăng nhập"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {
            'travelTypes': ['Biển', 'Núi'],
            'locations': ['Quảng Ninh', 'Lào Cai']
        }
        
        response = self.client.post(self.preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check preferences created
        preferences = TravelPreference.objects.filter(user=self.user)
        self.assertEqual(preferences.count(), 4)  # 2 types x 2 locations
    
    def test_save_preferences_unauthenticated(self):
        """Test lưu preferences khi chưa đăng nhập"""
        data = {
            'travelTypes': ['Biển'],
            'locations': ['Quảng Ninh']
        }
        
        response = self.client.post(self.preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_preferences(self):
        """Test cập nhật preferences (xóa cũ, tạo mới)"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create old preferences
        TravelPreference.objects.create(
            user=self.user,
            travel_type='Biển',
            location='Đà Nẵng'
        )
        
        # Update with new preferences
        data = {
            'travelTypes': ['Núi'],
            'locations': ['Sapa']
        }
        
        response = self.client.post(self.preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check old preferences deleted
        preferences = TravelPreference.objects.filter(user=self.user)
        self.assertEqual(preferences.count(), 1)
        self.assertEqual(preferences.first().travel_type, 'Núi')
        self.assertEqual(preferences.first().location, 'Sapa')


class AuthenticationIntegrationTest(TestCase):
    """Integration test cho authentication flow"""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_complete_auth_flow(self):
        """Test complete authentication flow"""
        # 1. Register
        register_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'newpass123'
        }
        
        response = self.client.post('/auth/register', register_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        access_token = response.data['tokens']['access']
        
        # 2. Save preferences
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        preferences_data = {
            'travelTypes': ['Biển', 'Núi'],
            'locations': ['Quảng Ninh']
        }
        
        response = self.client.post(
            reverse('save_preferences'), 
            preferences_data, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Verify preferences saved
        user = User.objects.get(username='newuser')
        preferences = TravelPreference.objects.filter(user=user)
        self.assertEqual(preferences.count(), 2)  # 2 types x 1 location
        
        # 4. Login again
        self.client.credentials()  # Clear credentials
        
        login_data = {
            'email': 'newuser@example.com',
            'password': 'newpass123'
        }
        
        response = self.client.post('/auth/login', login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
