from django.urls import include, path

from . import views

app_name = 'authentication'

urlpatterns = [
    # Inscription & Connexion
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # JWT
    path('token/refresh/', views.CustomTokenRefreshView.as_view(), name='token-refresh'),

    # Mot de passe
    path('password/change/', views.ChangePasswordView.as_view(), name='password-change'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # OAuth social (Google, Facebook via allauth)
    path('social/', include('allauth.socialaccount.urls')),
]
