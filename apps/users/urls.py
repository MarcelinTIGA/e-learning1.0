from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('me/', views.MeView.as_view(), name='me'),
    path('', views.UserListView.as_view(), name='user-list'),
    path('<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
]
