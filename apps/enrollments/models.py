"""
Modèles pour l'app 'enrollments' (Inscriptions & Paiements).

Flux principal :
    1. L'apprenant demande à s'inscrire → Enrollment(status=PENDING) créé
    2. Un paiement est initié              → Payment(status=PENDING) créé
    3. L'opérateur mobile confirme         → Payment(status=SUCCESS) + Enrollment(status=ACTIVE)
    4. Si le paiement échoue              → Payment(status=FAILED) + Enrollment(status=CANCELLED)

Formation gratuite (prix=0) :
    → Enrollment(status=ACTIVE) directement, sans Payment.
"""

from django.conf import settings
from django.db import models


class Enrollment(models.Model):
    """
    Représente l'inscription d'un apprenant à une formation.

    Un apprenant ne peut s'inscrire qu'UNE SEULE FOIS à une formation donnée
    (contrainte unique_together). Le statut évolue selon l'avancement du paiement.
    """

    # ── Statuts possibles d'une inscription ──────────────────────────────────
    class Status(models.TextChoices):
        PENDING   = 'pending',   'En attente'    # Paiement pas encore confirmé
        ACTIVE    = 'active',    'Active'         # Paiement validé, accès accordé
        COMPLETED = 'completed', 'Terminée'       # L'apprenant a fini la formation
        CANCELLED = 'cancelled', 'Annulée'        # Paiement échoué ou annulé

    # ── Relations ─────────────────────────────────────────────────────────────
    # L'apprenant qui s'inscrit
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,       # Si l'utilisateur est supprimé, ses inscriptions aussi
        related_name='enrollments',     # user.enrollments.all()
    )

    # La formation à laquelle il s'inscrit
    formation = models.ForeignKey(
        'courses.Formation',
        on_delete=models.CASCADE,       # Si la formation est supprimée, les inscriptions aussi
        related_name='enrollments',     # formation.enrollments.all()
    )

    # ── Statut de l'inscription ───────────────────────────────────────────────
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,         # Par défaut : en attente de paiement
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    enrolled_at = models.DateTimeField(auto_now_add=True)   # Date d'inscription (immuable)
    updated_at  = models.DateTimeField(auto_now=True)       # Dernière modification

    # ── Contrainte métier : un apprenant ne peut s'inscrire qu'une seule fois ─
    class Meta:
        # Interdit d'avoir deux Enrollment pour le même (user, formation)
        unique_together = ('user', 'formation')
        ordering = ['-enrolled_at']  # Plus récentes en premier

    def __str__(self):
        return f"{self.user.email} → {self.formation.titre} ({self.status})"

    # ── Propriétés utilitaires ─────────────────────────────────────────────────

    @property
    def is_active(self):
        """
        Vrai si l'apprenant a accès au contenu de la formation.
        Utilisé par la permission IsEnrolledAndPaid.
        """
        return self.status == self.Status.ACTIVE

    @property
    def is_paid(self):
        """
        Vrai si l'inscription est active ou complétée (paiement effectué).
        Différent de is_active : une inscription COMPLETED était aussi payée.
        """
        return self.status in (self.Status.ACTIVE, self.Status.COMPLETED)


class Payment(models.Model):
    """
    Représente le paiement associé à une inscription.

    Un seul paiement par inscription (OneToOneField).
    Les formations gratuites n'ont PAS de Payment — on accorde l'accès directement.

    Pour l'instant, OrangeMoney et MTN MoMo sont des stubs (simulation).
    L'intégration réelle viendra quand les API bancaires seront disponibles.
    """

    # ── Opérateurs de paiement Mobile Money supportés ─────────────────────────
    class Provider(models.TextChoices):
        ORANGE = 'orange_money', 'Orange Money'  # Orange Money Cameroun
        MTN    = 'mtn_momo',     'MTN MoMo'      # MTN Mobile Money

    # ── Statuts possibles du paiement ─────────────────────────────────────────
    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'   # Paiement initié, en cours
        SUCCESS = 'success', 'Réussi'       # Paiement confirmé par l'opérateur
        FAILED  = 'failed',  'Échoué'       # Refusé ou timeout

    # ── Lien avec l'inscription (1 paiement = 1 inscription) ──────────────────
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,       # Si l'inscription est supprimée, le paiement aussi
        related_name='payment',         # enrollment.payment
    )

    # ── Détails financiers ────────────────────────────────────────────────────
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        # On utilise DecimalField (pas FloatField) pour éviter les erreurs d'arrondi
        # Exemple : 15000.00 XAF, pas 14999.999999...
    )

    # Devise fixe : XAF = Franc CFA (monnaie d'Afrique Centrale)
    currency = models.CharField(max_length=3, default='XAF')

    # ── Informations Mobile Money ─────────────────────────────────────────────
    provider = models.CharField(
        max_length=15,
        choices=Provider.choices,       # Seulement Orange ou MTN
    )

    # Numéro de téléphone qui effectue le paiement (ex: +237 655 000 000)
    phone_number = models.CharField(max_length=20)

    # ID de transaction renvoyé par l'opérateur après confirmation
    # blank=True car on ne l'a pas encore au moment d'initier le paiement
    transaction_id = models.CharField(max_length=100, blank=True, default='')

    # ── Statut du paiement ────────────────────────────────────────────────────
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,         # Par défaut : en attente de confirmation
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    initiated_at = models.DateTimeField(auto_now_add=True)  # Quand le paiement a été initié
    updated_at   = models.DateTimeField(auto_now=True)      # Dernière mise à jour

    def __str__(self):
        return (
            f"Paiement {self.provider} — {self.amount} {self.currency} "
            f"({self.status}) pour {self.enrollment}"
        )
