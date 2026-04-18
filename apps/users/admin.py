from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_also_admin', 'is_active')
    list_filter = ('role', 'is_also_admin', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name')}),
        ('Rôles', {'fields': ('role', 'is_also_admin')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        # Sur la création (obj=None) : pas d'inline profil,
        # le signal post_save le crée automatiquement.
        # Sur l'édition : l'inline apparaît pour modifier phone/bio/avatar.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)
