"""Administration Django pour l'app 'enrollments'."""

from django.contrib import admin

from .models import Enrollment, Payment


class PaymentInline(admin.StackedInline):
    """
    Affiche le paiement associé directement dans la page d'une inscription.
    StackedInline = affichage vertical (plus lisible pour un seul objet).
    """

    model = Payment
    extra = 0   # Pas de formulaire vide pour créer un paiement
    readonly_fields = ('initiated_at', 'updated_at', 'transaction_id')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'formation', 'status', 'enrolled_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'formation__titre')
    readonly_fields = ('enrolled_at', 'updated_at')
    inlines = [PaymentInline]
    ordering = ('-enrolled_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'provider', 'amount', 'currency', 'status', 'initiated_at')
    list_filter = ('provider', 'status')
    search_fields = ('enrollment__user__email', 'transaction_id')
    readonly_fields = ('initiated_at', 'updated_at')
    ordering = ('-initiated_at',)
