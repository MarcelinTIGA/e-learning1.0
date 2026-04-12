"""
Configuration de l'app 'progress'.

La méthode ready() est appelée par Django au démarrage, une fois
que toutes les apps sont chargées. C'est le bon endroit pour connecter
les signaux, car à ce stade tous les modèles sont disponibles.

Sans ready() → les signaux dans signals.py ne seraient jamais connectés
             → le signal post_save de QuizAttempt ne déclencherait rien.
"""

from django.apps import AppConfig


class ProgressConfig(AppConfig):
    name = 'apps.progress'

    def ready(self):
        """
        Importe signals.py pour connecter les signaux Django.

        L'import ici (et non au niveau du module) est intentionnel :
        les signaux ne doivent être connectés qu'une seule fois, après
        que toutes les apps Django sont initialisées.
        """
        # noqa: F401 = silence l'avertissement "imported but unused"
        import apps.progress.signals  # noqa: F401
