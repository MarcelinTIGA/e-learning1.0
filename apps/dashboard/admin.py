"""
Configuration du panel d'administration pour l'app 'dashboard'.

AMBIGUÏTÉ : Pourquoi un admin.py vide ?
  - Le dashboard n'a PAS de modèle propre (pas de table en BDD)
  - C'est une vue agrégée de données existantes
  - Le panel admin gère des modèles, pas des vues
  - Donc rien à enregistrer ici

Si on voulait un dashboard dans l'admin Django, il faudrait :
  1. Créer une vue admin custom (hériter de ModelAdmin ou TemplateView)
  2. Overrider le template admin/index.html
  3. Ou utiliser un package comme django-admin-tools
"""

# Rien à enregistrer — le dashboard n'a pas de modèles
