"""
Signals pour l'app 'certificates'.

Déclenche la création automatique d'un certificat quand un apprenant
termine une formation (progression = 100%).

AMBIGUÏTÉ : Pourquoi un signal et pas appeler le service directement depuis ProgressService ?
  - Découplage : l'app 'progress' ne doit pas dépendre de 'certificates'
  - Un signal permet d'ajouter d'autres actions futures (email, notification, badge)
    sans modifier le code de 'progress'
  - Les signaux sont le mécanisme Django recommandé pour la communication inter-apps
  - Inconvénient : plus difficile à debugger (exécution asynchrone apparente)

Où connecter le signal ?
  - Dans apps.py.ready() pour s'assurer qu'il n'est connecté qu'une seule fois
  - Évite les doublons si le module est importé plusieurs fois
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.progress.models import FormationProgress


@receiver(post_save, sender=FormationProgress)
def auto_generate_certificate(sender, instance, created, **kwargs):
    """
    Génère automatiquement un certificat quand la progression atteint 100%.

    AMBIGUÏTÉ : Pourquoi post_save et pas un signal personnalisé ?
      - post_save est le signal standard de Django
      - On vérifie is_completed dans le handler (pas besoin de signal custom)
      - Si on émettait un signal custom 'formation_completed', il faudrait
        le déclencher depuis ProgressService, ce qui couplerait les apps

    AMBIGUÏTÉ : Pourquoi ne pas utiliser 'created' pour ne déclencher qu'à la création ?
      - is_completed peut passer à True lors d'un UPDATE (pas uniquement à la création)
      - Ex: l'apprenant termine sa dernière leçon → FormationProgress est mis à jour
      - Donc on vérifie is_completed à chaque save, pas seulement à la création

    AMBIGUÏTÉ : Pourquoi ne pas envoyer un email de notification ici ?
      - L'envoi d'email est une opération I/O lente (SMTP)
      - Les signaux post_save sont synchrones : bloquer le request/response
      - En production, on utiliserait un task queue (Celery) pour l'email
      - Pour l'instant, on se contente de créer le certificat
    """
    # Ne générer que si la formation est complétée
    if not instance.is_completed:
        return

    # Éviter les imports circulaires en important ici plutôt qu'en haut du fichier
    # AMBIGUÏTÉ : Pourquoi pas en haut ?
    #   - FormationProgress import Certificate → Certificate import CertificateService
    #     → CertificateService import FormationProgress = import circulaire
    #   - Importer dans la fonction casse le cycle
    from apps.certificates.models import Certificate
    from apps.certificates.services import CertificateService

    # Vérifier qu'un certificat n'existe pas déjà (sécurité)
    if Certificate.objects.filter(user=instance.user, formation=instance.formation).exists():
        return

    try:
        CertificateService.create_certificate(
            user=instance.user,
            formation=instance.formation,
        )
    except Exception:
        # AMBIGUÏTÉ : Pourquoi silencer les erreurs ?
        #   - Un signal ne devrait pas casser la requête principale
        #   - Si la génération du certificat échoue, l'apprenant a quand même
        #     terminé sa formation. On ne veut pas rollback la progression.
        #   - En production : logger l'erreur + alerter l'admin
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(
            f"Échec de génération du certificat pour "
            f"user={instance.user.pk}, formation={instance.formation.pk}"
        )
