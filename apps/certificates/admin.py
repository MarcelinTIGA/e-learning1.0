"""
Configuration du panel d'administration pour l'app 'certificates'.
"""

from django.contrib import admin

from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """Administration des certificats."""

    list_display = (
        'verification_code', 'user', 'formation_titre_snapshot',
        'issued_at', 'has_pdf',
    )
    list_filter = ('issued_at',)
    search_fields = (
        'verification_code', 'user__email', 'user__first_name',
        'user__last_name', 'formation_titre_snapshot',
    )
    readonly_fields = (
        'id', 'verification_code', 'formation_titre_snapshot',
        'formation_duration_snapshot', 'issued_at', 'pdf_file',
    )
    date_hierarchy = 'issued_at'

    def has_pdf(self, obj):
        """Indique si le PDF a été généré."""
        return bool(obj.pdf_file)
    has_pdf.boolean = True
    has_pdf.short_description = 'PDF généré'

    def has_add_permission(self, request):
        """
        AMBIGUÏTÉ : Pourquoi interdire l'ajout depuis l'admin ?
          - Les certificats sont créés automatiquement (via signal ou API)
          - L'admin Django ne gère pas la génération du PDF
          - Permettre l'ajout créerait des certificats sans PDF
          - Les admins doivent passer par l'API POST /api/certificates/
        """
        return False
