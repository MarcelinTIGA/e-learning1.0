from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.certificates'

    def ready(self):
        """
        Connecte les signals automatiquement au démarrage de l'app.

        AMBIGUÏTÉ : Pourquoi dans ready() et pas en haut de models.py ou signals.py ?
          - Si on importe les signals en haut de models.py, l'import circulaire
            se produit (FormationProgress → Certificate → CertificateService → FormationProgress)
          - Si on importe en haut de signals.py, le module n'est jamais chargé
            sauf si quelqu'un fait explicitement `import apps.certificates.signals`
          - ready() est appelé APRÈS le chargement de tous les modèles
            → pas de risque d'import circulaire
          - Le décorateur @receiver ne fonctionne que si le module est importé
            → ready() garantit que le module signals est importé une seule fois
        """
        import apps.certificates.signals  # noqa: F401
