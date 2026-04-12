from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import User
from .permissions import IsAdministrateur
from .serializers import UserSerializer, UserUpdateSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """GET /api/users/me/ — profil courant. PATCH /api/users/me/ — mise à jour."""
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer


class UserListView(generics.ListAPIView):
    """GET /api/users/ — liste des utilisateurs (admin uniquement)."""
    queryset = User.objects.select_related('profile').order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdministrateur]
    search_fields = ['email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active']


class UserDetailView(generics.RetrieveAPIView):
    """GET /api/users/{id}/ — détail d'un utilisateur (admin uniquement)."""
    queryset = User.objects.select_related('profile').all()
    serializer_class = UserSerializer
    permission_classes = [IsAdministrateur]
