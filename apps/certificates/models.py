"""
Modèles de l'app 'certificates' — Délivrance de certificats PDF.

Flux principal :
    1. L'apprenant termine une formation (progression = 100%)
    2. Un Certificate est automatiquement créé (via signal)
    3. Le PDF est généré avec reportlab
    4. L'apprenant peut télécharger son certificat

Pourquoi stocker le PDF plutôt que le générer à la volée ?
    - Traçabilité : le PDF ne change pas même si le template évolue
    - Performance : pas de régénération à chaque téléchargement
    - Légalité : le certificat est un document officiel, il doit être immuable

Pourquoi un code de vérification unique ?
    - Permet à un employeur de vérifier l'authenticité d'un certificat
    - URL : /api/certificates/verify/<code>/ retourne les infos du certificat
"""

import uuid

from django.db import models


class Certificate(models.Model):
    """
    Certificat délivré à un apprenant après avoir complété une formation.

    Un apprenant ne peut avoir qu'UN SEUL certificat par formation
    (contrainte unique_together). Le certificat est immuable après création.
    """

    # ── Identifiant unique ────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Relations ─────────────────────────────────────────────────────────────
    # L'apprenant qui reçoit le certificat
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='certificates',
    )

    # La formation complétée
    formation = models.ForeignKey(
        'courses.Formation',
        on_delete=models.CASCADE,
        related_name='certificates',
    )

    # ── Code de vérification unique ──────────────────────────────────────────
    # Ex: "CERT-2024-A1B2C3D4"
    # Généré automatiquement dans save()
    verification_code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Code unique pour vérifier l'authenticité du certificat",
    )

    # ── Fichier PDF ──────────────────────────────────────────────────────────
    # Stocké dans media/certificates/
    # Généré automatiquement par CertificateService.generate_pdf()
    pdf_file = models.FileField(
        upload_to='certificates/pdfs/',
        blank=True,
        null=True,
        help_text="Fichier PDF généré automatiquement",
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    issued_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de délivrance (immuable)",
    )

    # ── Métadonnées (copies des données de la formation) ──────────────────────
    # AMBIGUÏTÉ : Pourquoi copier ces données au lieu de les lire depuis Formation ?
    #   - Si le formateur modifie le titre de sa formation APRÈS la délivrance,
    #     le certificat doit garder l'ancien titre (document historique).
    #   - C'est une copie "snapshot" de l'état de la formation à la délivrance.
    formation_titre_snapshot = models.CharField(max_length=200, editable=False)
    formation_duration_snapshot = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Durée totale de la formation en minutes (au moment de la délivrance)",
    )

    class Meta:
        db_table = 'certificates'
        # Un seul certificat par (user, formation)
        unique_together = ('user', 'formation')
        ordering = ['-issued_at']
        verbose_name = 'Certificat'
        verbose_name_plural = 'Certificats'

    def __str__(self):
        return f"Certificat — {self.user.email} → {self.formation_titre_snapshot}"

    def save(self, *args, **kwargs):
        """
        Génère automatiquement le code de vérification et le snapshot
        lors de la première création.
        """
        if not self.verification_code:
            self.verification_code = self._generate_verification_code()

        # Snapshot des données de la formation (uniquement à la création)
        # AMBIGUÏTÉ : self.pk est None pour un nouvel objet, mais self.formation
        #   peut être None si le Certificate est créé sans FK explicite.
        #   On vérifie les deux conditions.
        is_new = self._state.adding  # Plus fiable que `not self.pk`
        if is_new and self.formation:
            self.formation_titre_snapshot = self.formation.titre
            # Calcul de la durée totale depuis les leçons
            total_minutes = 0
            for module in self.formation.modules.all():
                for lesson in module.lessons.all():
                    total_minutes += lesson.duration_minutes
            self.formation_duration_snapshot = total_minutes

        super().save(*args, **kwargs)

    def _generate_verification_code(self):
        """
        Génère un code unique du format : CERT-AAAA-XXXXXXXX
        Où AAAA = année, XXXXXXXX = 8 caractères hexadécimaux uniques.

        AMBIGUÏTÉ : Pourquoi pas un UUID complet ?
          - Un UUID est trop long pour être tapé manuellement par un employeur.
          - 8 caractères hex offrent ~4 milliards de combinaisons (suffisant).
          - Le préfixe avec l'année facilite le tri manuel.
        """
        import datetime
        year = datetime.datetime.now().year
        unique_part = str(uuid.uuid4()).replace('-', '')[:8].upper()
        return f"CERT-{year}-{unique_part}"
