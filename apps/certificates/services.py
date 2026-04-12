"""
Services pour l'app 'certificates'.

Contient :
  - CertificateService : création de certificats
  - PDFGenerator       : génération du PDF avec reportlab
"""

import io
import os

from django.conf import settings
from django.core.files.base import ContentFile

from .models import Certificate


class PDFGenerator:
    """
    Génère un certificat PDF avec reportlab.

    AMBIGUÏTÉ : Pourquoi reportlab et pas un template HTML + WeasyPrint ?
      - reportlab est déjà dans requirements.txt (dépendance existante)
      - WeasyPrint nécessite des bibliothèques système (Cairo, Pango)
        qui compliquent le déploiement
      - reportlab est plus léger et suffisant pour un certificat simple

    AMBIGUÏTÉ : Pourquoi un design en code et pas un template PDF ?
      - Un template PDF serait plus flexible mais nécessite un fichier externe
      - Le code est plus maintenable : pas de fichier binaire à versionner
      - On pourrait évoluer vers un template plus tard (stocker dans media/templates/)
    """

    # Couleurs (format RGB pour reportlab)
    COLOR_PRIMARY = (0.15, 0.35, 0.65)    # Bleu foncé professionnel
    COLOR_SECONDARY = (0.85, 0.65, 0.15)  # Or pour le décor
    COLOR_TEXT = (0.2, 0.2, 0.2)          # Gris foncé pour le texte
    COLOR_LIGHT = (0.75, 0.75, 0.75)     # Gris clair pour les lignes

    # Dimensions (en points, format A4 = 595 x 842 points)
    PAGE_WIDTH = 595
    PAGE_HEIGHT = 842

    @classmethod
    def generate(cls, certificate):
        """
        Génère le PDF pour un certificat et le stocke dans le modèle.

        Args:
            certificate: instance de Certificate

        Returns:
            bytes: le contenu du PDF
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # ── Cadre décoratif ──────────────────────────────────────────────────
        # Double bordure : une épaisse + une fine pour l'effet "diplôme"
        c.setStrokeColorRGB(*cls.COLOR_PRIMARY)
        c.setLineWidth(3)
        c.rect(15 * mm, 15 * mm, width - 30 * mm, height - 30 * mm)
        c.setLineWidth(1)
        c.rect(18 * mm, 18 * mm, width - 36 * mm, height - 36 * mm)

        # ── Lignes décoratives en haut et en bas ─────────────────────────────
        c.setStrokeColorRGB(*cls.COLOR_SECONDARY)
        c.setLineWidth(2)
        # Ligne haute
        c.line(40 * mm, height - 60 * mm, width - 40 * mm, height - 60 * mm)
        # Ligne basse
        c.line(40 * mm, 60 * mm, width - 40 * mm, 60 * mm)

        # ── Titre "CERTIFICAT" ───────────────────────────────────────────────
        c.setFillColorRGB(*cls.COLOR_PRIMARY)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(width / 2, height - 90 * mm, "CERTIFICAT")

        # ── Sous-titre ──────────────────────────────────────────────────────
        c.setFont("Helvetica", 16)
        c.setFillColorRGB(*cls.COLOR_TEXT)
        c.drawCentredString(
            width / 2, height - 110 * mm,
            "de réussite à la formation"
        )

        # ── Nom de l'apprenant ──────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 28)
        c.setFillColorRGB(*cls.COLOR_TEXT)
        c.drawCentredString(
            width / 2, height - 150 * mm,
            certificate.user.full_name
        )

        # ── Ligne sous le nom ───────────────────────────────────────────────
        c.setStrokeColorRGB(*cls.COLOR_SECONDARY)
        c.setLineWidth(1)
        name_width = c.stringWidth(certificate.user.full_name, "Helvetica-Bold", 28)
        name_x = (width - name_width) / 2
        c.line(name_x, height - 160 * mm, name_x + name_width, height - 160 * mm)

        # ── Texte de mention ────────────────────────────────────────────────
        c.setFont("Helvetica", 14)
        c.setFillColorRGB(*cls.COLOR_TEXT)
        c.drawCentredString(
            width / 2, height - 190 * mm,
            "a complété avec succès la formation"
        )

        # ── Nom de la formation ─────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 22)
        c.setFillColorRGB(*cls.COLOR_PRIMARY)
        c.drawCentredString(
            width / 2, height - 225 * mm,
            certificate.formation_titre_snapshot
        )

        # ── Durée ───────────────────────────────────────────────────────────
        duration = certificate.formation_duration_snapshot
        if duration > 0:
            hours = duration // 60
            minutes = duration % 60
            if hours > 0:
                duration_text = f"Durée : {hours}h"
                if minutes > 0:
                    duration_text += f" {minutes}min"
            else:
                duration_text = f"Durée : {minutes} minutes"

            c.setFont("Helvetica-Oblique", 12)
            c.setFillColorRGB(*cls.COLOR_LIGHT)
            c.drawCentredString(width / 2, height - 250 * mm, duration_text)

        # ── Date de délivrance ──────────────────────────────────────────────
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(*cls.COLOR_TEXT)
        date_str = certificate.issued_at.strftime("%d %B %Y")
        # Traduction manuelle des mois (reportlab ne gère pas i18n simplement)
        mois_fr = {
            'January': 'janvier', 'February': 'février', 'March': 'mars',
            'April': 'avril', 'May': 'mai', 'June': 'juin',
            'July': 'juillet', 'August': 'août', 'September': 'septembre',
            'October': 'octobre', 'November': 'novembre', 'December': 'décembre',
        }
        for eng, fr in mois_fr.items():
            date_str = date_str.replace(eng, fr)

        c.drawCentredString(
            width / 2, height - 300 * mm,
            f"Délivré le {date_str}"
        )

        # ── Code de vérification ────────────────────────────────────────────
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColorRGB(*cls.COLOR_LIGHT)
        c.drawCentredString(
            width / 2, 40 * mm,
            f"Code de vérification : {certificate.verification_code}"
        )

        # ── Signature (ligne) ───────────────────────────────────────────────
        c.setStrokeColorRGB(*cls.COLOR_TEXT)
        c.setLineWidth(0.5)
        sig_x = width - 120 * mm
        sig_y = 65 * mm
        c.line(sig_x, sig_y, sig_x + 80 * mm, sig_y)
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColorRGB(*cls.COLOR_TEXT)
        c.drawCentredString(sig_x + 40 * mm, sig_y - 5 * mm, "Direction de la formation")

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def save_to_model(cls, certificate):
        """
        Génère le PDF et le sauvegarde dans le champ pdf_file du certificat.

        Args:
            certificate: instance de Certificate
        """
        pdf_content = cls.generate(certificate)

        # Nom du fichier : CERT-2024-A1B2C3D4.pdf
        filename = f"{certificate.verification_code}.pdf"

        # AMBIGUÏTÉ : Pourquoi ContentFile et pas écrire directement sur le disque ?
        #   - Django's FileField attend un fichier "file-like"
        #   - ContentFile permet de passer des bytes en mémoire sans écrire sur le disque
        #   - Le storage backend (par défaut FileSystemStorage) s'occupe de l'écriture
        certificate.pdf_file.save(filename, ContentFile(pdf_content), save=True)


class CertificateService:
    """Opérations métier sur les certificats."""

    @staticmethod
    def create_certificate(user, formation):
        """
        Crée un certificat pour un utilisateur et une formation.

        AMBIGUÏTÉ : Pourquoi vérifier la progression avant de créer ?
          - Le signal est censé ne se déclencher qu'à 100%, mais on ajoute
            une sécurité au cas où quelqu'un appelle ce service manuellement.
          - Double vérification : mieux vaut prévenir que guérir.

        Args:
            user: l'apprenant
            formation: la formation complétée

        Returns:
            Certificate: le certificat créé

        Raises:
            ValueError: si un certificat existe déjà ou si la formation n'est pas terminée
        """
        # Vérifier qu'un certificat n'existe pas déjà
        if Certificate.objects.filter(user=user, formation=formation).exists():
            raise ValueError("Un certificat existe déjà pour cette formation.")

        # Vérifier que la formation est terminée (progression 100%)
        from apps.progress.models import FormationProgress
        try:
            progress = FormationProgress.objects.get(user=user, formation=formation)
            if not progress.is_completed:
                raise ValueError(
                    f"La formation n'est pas terminée (progression : {progress}%)."
                )
        except FormationProgress.DoesNotExist:
            raise ValueError("Aucune progression trouvée pour cette formation.")

        # Créer le certificat
        certificate = Certificate.objects.create(
            user=user,
            formation=formation,
        )

        # Générer et sauvegarder le PDF
        PDFGenerator.save_to_model(certificate)

        return certificate

    @staticmethod
    def verify_certificate(code):
        """
        Vérifie l'authenticité d'un certificat par son code.

        Args:
            code: le code de vérification (ex: "CERT-2024-A1B2C3D4")

        Returns:
            dict: {'is_valid': bool, 'message': str, 'certificate': Certificate|None}
        """
        try:
            certificate = Certificate.objects.select_related(
                'user', 'formation'
            ).get(verification_code=code)
            return {
                'is_valid': True,
                'message': "Certificat authentique.",
                'certificate': certificate,
            }
        except Certificate.DoesNotExist:
            return {
                'is_valid': False,
                'message': "Code de vérification invalide.",
                'certificate': None,
            }
