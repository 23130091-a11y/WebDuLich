from django.urls import path

from .views import RegisterView, LoginView, save_preferences

urlpatterns = [
    ## auth/register
    path('register', RegisterView.as_view()),
    path('login', LoginView.as_view()),
    path('preferences', save_preferences, name='save_preferences'),
    # path('preferences', get_preferences, name='get_preferences'),   # GET
    # path('preferences/save', save_preferences, name='save_preferences'), # POST
]