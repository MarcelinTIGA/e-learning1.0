"""
Services métier pour l'app 'enrollments'.

Ce fichier contient TOUTE la logique d'inscription et de paiement.
Les views Django sont volontairement "bêtes" : elles reçoivent la requête,
délèguent au service, et retournent la réponse. La logique est ici.

Pourquoi séparer services et views ?
    → Testabilité : on peut tester la logique sans simuler des requêtes HTTP
    → Réutilisabilité : un service peut être appelé depuis plusieurs endroits
    → Lisibilité : les views restent courtes, la complexité est isolée ici

Architecture des passerelles de paiement :
    PaymentService (orchestrateur)
        ├── OrangeMoneyGateway (stub Orange Money)
        └── MTNMoMoGateway    (stub MTN MoMo)

"stub" = simulation. Les appels API réels arrivent quand on a les credentials.
"""

import logging

from django.db import transaction

from apps.courses.models import Formation

from .models import Enrollment, Payment

# Logger Django pour tracer les opérations importantes
# Utilisation : logger.info("message"), logger.error("message"), etc.
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PASSERELLES DE PAIEMENT (STUBS)
# ─────────────────────────────────────────────────────────────────────────────

class OrangeMoneyGateway:
    """
    Passerelle de paiement Orange Money (simulation).

    Dans la vraie vie, cette classe ferait des appels HTTP à l'API Orange Money
    Cameroun. Pour l'instant, c'est un STUB : elle simule toujours un succès.

    Interface à respecter pour la vraie intégration :
        - initiate_payment() : initier le paiement, retourner un transaction_id
        - verify_payment()   : vérifier si un paiement a été confirmé
    """

    def initiate_payment(self, phone_number: str, amount: float, reference: str) -> dict:
        """
        Initie un paiement Orange Money.

        Args:
            phone_number: Numéro de téléphone Orange (ex: +237655000000)
            amount:       Montant en XAF
            reference:    Référence unique de la transaction (ex: enrollment_42)

        Returns:
            dict avec 'success' (bool), 'transaction_id' (str), 'message' (str)

        TODO: Remplacer par un vrai appel à l'API Orange Money Cameroun.
              URL : https://api.orange.com/orange-money-webpay/cm/v1/
              Clés API nécessaires : CLIENT_ID, CLIENT_SECRET (dans settings.py)
        """
        logger.info(
            f"[OrangeMoney STUB] Paiement initié : {amount} XAF pour {phone_number}"
        )

        # STUB : on simule un succès immédiat avec un faux transaction_id
        return {
            'success': True,
            'transaction_id': f'ORANGE_STUB_{reference}',
            'message': 'Paiement Orange Money simulé avec succès.',
        }

    def verify_payment(self, transaction_id: str) -> dict:
        """
        Vérifie le statut d'un paiement Orange Money.

        Args:
            transaction_id: L'ID renvoyé par initiate_payment()

        Returns:
            dict avec 'status' ('success' | 'pending' | 'failed')

        TODO: Appel API réel pour vérifier si l'utilisateur a confirmé
              le paiement sur son téléphone.
        """
        logger.info(f"[OrangeMoney STUB] Vérification paiement : {transaction_id}")

        # STUB : on suppose que tout paiement initié est un succès
        return {'status': 'success'}


class MTNMoMoGateway:
    """
    Passerelle de paiement MTN Mobile Money (simulation).

    Même logique que OrangeMoneyGateway mais pour MTN.

    TODO: Vraie intégration via l'API MTN MoMo :
          URL : https://sandbox.momodeveloper.mtn.com/
          Clés API : MTN_MOMO_SUBSCRIPTION_KEY, MTN_MOMO_API_USER, etc.
    """

    def initiate_payment(self, phone_number: str, amount: float, reference: str) -> dict:
        """Initie un paiement MTN MoMo (stub)."""
        logger.info(
            f"[MTNMoMo STUB] Paiement initié : {amount} XAF pour {phone_number}"
        )
        return {
            'success': True,
            'transaction_id': f'MTN_STUB_{reference}',
            'message': 'Paiement MTN MoMo simulé avec succès.',
        }

    def verify_payment(self, transaction_id: str) -> dict:
        """Vérifie le statut d'un paiement MTN MoMo (stub)."""
        logger.info(f"[MTNMoMo STUB] Vérification paiement : {transaction_id}")
        return {'status': 'success'}


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE D'INSCRIPTION ET DE PAIEMENT
# ─────────────────────────────────────────────────────────────────────────────

# Registre des passerelles disponibles.
# Pour ajouter un nouveau provider, il suffit de l'ajouter ici.
# La clé correspond à Payment.Provider.value (ex: 'orange_money').
PAYMENT_GATEWAYS = {
    'orange_money': OrangeMoneyGateway(),
    'mtn_momo':     MTNMoMoGateway(),
}


class EnrollmentService:
    """
    Orchestrateur des inscriptions et paiements.

    Cette classe gère tout le flux :
        1. Vérifications préalables (formation publiée, pas déjà inscrit, etc.)
        2. Création de l'Enrollment
        3. Gestion des formations gratuites (accès direct)
        4. Initiation du paiement pour les formations payantes
        5. Mise à jour du statut après confirmation du paiement
    """

    @staticmethod
    @transaction.atomic
    def enroll(user, formation_id: int, phone_number: str = None, provider: str = None) -> Enrollment:
        """
        Inscrit un apprenant à une formation.

        Flux selon le prix :
            - Formation GRATUITE → Enrollment(ACTIVE) directement, pas de Payment
            - Formation PAYANTE  → Enrollment(PENDING) + Payment(PENDING) + appel gateway

        @transaction.atomic : si quelque chose échoue à mi-chemin
        (ex: création Payment échoue), l'Enrollment est aussi annulé.
        On ne veut pas d'Enrollment sans Payment pour une formation payante.

        Args:
            user:         L'utilisateur qui s'inscrit
            formation_id: L'ID de la formation
            phone_number: Numéro de téléphone pour le paiement Mobile Money
            provider:     'orange_money' ou 'mtn_momo'

        Returns:
            L'objet Enrollment créé

        Raises:
            ValueError:          Données invalides ou règle métier non respectée
            Formation.DoesNotExist: Formation introuvable
        """
        # ── 1. Récupérer la formation ─────────────────────────────────────────
        formation = Formation.objects.get(pk=formation_id)

        # Vérifier que la formation est bien publiée
        if not formation.is_published:
            raise ValueError("Cette formation n'est pas encore disponible.")

        # ── 2. Vérifier si l'apprenant est déjà inscrit ───────────────────────
        # get_or_create retourne (objet, created) — created=True si nouvel objet
        enrollment, created = Enrollment.objects.get_or_create(
            user=user,
            formation=formation,
        )

        if not created:
            # L'apprenant est déjà inscrit — pas besoin de recréer
            raise ValueError("Vous êtes déjà inscrit à cette formation.")

        # ── 3. Formation gratuite → accès immédiat ────────────────────────────
        if formation.is_free:
            # is_free = (prix == 0), voir Formation.is_free property dans courses/models.py
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            logger.info(
                f"Inscription GRATUITE : {user.email} → {formation.titre}"
            )
            return enrollment

        # ── 4. Formation payante → initier le paiement ────────────────────────
        if not phone_number or not provider:
            raise ValueError(
                "Un numéro de téléphone et un opérateur sont requis pour les formations payantes."
            )

        if provider not in PAYMENT_GATEWAYS:
            raise ValueError(
                f"Opérateur invalide : '{provider}'. Choisir 'orange_money' ou 'mtn_momo'."
            )

        # Créer le paiement en base (statut PENDING pour l'instant)
        payment = Payment.objects.create(
            enrollment=enrollment,
            amount=formation.prix,          # Prix de la formation
            currency='XAF',
            provider=provider,
            phone_number=phone_number,
            status=Payment.Status.PENDING,
        )

        # Appeler la passerelle de paiement correspondante
        gateway = PAYMENT_GATEWAYS[provider]
        reference = f"enrollment_{enrollment.pk}"  # Référence unique de transaction

        result = gateway.initiate_payment(
            phone_number=phone_number,
            amount=float(formation.prix),
            reference=reference,
        )

        if result.get('success'):
            # Sauvegarder le transaction_id renvoyé par l'opérateur
            payment.transaction_id = result.get('transaction_id', '')
            payment.save()
            logger.info(
                f"Paiement initié : {user.email} → {formation.titre} "
                f"via {provider} (txn: {payment.transaction_id})"
            )
        else:
            # L'opérateur a refusé d'initier le paiement
            payment.status = Payment.Status.FAILED
            payment.save()
            enrollment.status = Enrollment.Status.CANCELLED
            enrollment.save()
            raise ValueError(f"Échec de l'initiation du paiement : {result.get('message')}")

        return enrollment

    @staticmethod
    @transaction.atomic
    def confirm_payment(enrollment_id: int) -> Enrollment:
        """
        Confirme un paiement et active l'inscription.

        Appelé par :
            - Le webhook de l'opérateur (quand il notifie le succès)
            - Manuellement par un admin pour débloquer un apprenant
            - Les tests automatisés pour simuler une confirmation

        Args:
            enrollment_id: L'ID de l'Enrollment à activer

        Returns:
            L'Enrollment mis à jour (status=ACTIVE)

        Raises:
            Enrollment.DoesNotExist: Inscription introuvable
            ValueError:             Pas de paiement associé ou déjà confirmé
        """
        # select_related('payment') : charge le Payment en une seule requête SQL
        enrollment = Enrollment.objects.select_related('payment').get(pk=enrollment_id)

        # Vérifier qu'il y a bien un paiement associé
        if not hasattr(enrollment, 'payment'):
            raise ValueError("Aucun paiement associé à cette inscription.")

        # Vérifier que l'inscription est bien en attente (pas déjà active)
        if enrollment.status != Enrollment.Status.PENDING:
            raise ValueError(f"L'inscription est déjà en statut '{enrollment.status}'.")

        # Mettre à jour le paiement et l'inscription
        enrollment.payment.status = Payment.Status.SUCCESS
        enrollment.payment.save()

        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.save()

        logger.info(
            f"Inscription activée : {enrollment.user.email} → {enrollment.formation.titre}"
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def cancel_enrollment(enrollment_id: int) -> Enrollment:
        """
        Annule une inscription et marque le paiement comme échoué.

        Utilisé quand :
            - L'opérateur notifie un échec de paiement (webhook)
            - L'apprenant annule sa demande
            - Un admin annule manuellement

        Args:
            enrollment_id: L'ID de l'Enrollment à annuler

        Returns:
            L'Enrollment mis à jour (status=CANCELLED)
        """
        enrollment = Enrollment.objects.select_related('payment').get(pk=enrollment_id)

        enrollment.status = Enrollment.Status.CANCELLED
        enrollment.save()

        # Si un paiement existe, le marquer comme échoué aussi
        if hasattr(enrollment, 'payment') and enrollment.payment.status == Payment.Status.PENDING:
            enrollment.payment.status = Payment.Status.FAILED
            enrollment.payment.save()

        logger.info(
            f"Inscription annulée : {enrollment.user.email} → {enrollment.formation.titre}"
        )
        return enrollment
