"""
Serializers pour l'app 'dashboard'.

  - StudentDashboardSerializer   : vue d'ensemble apprenant
  - FormateurDashboardSerializer : vue d'ensemble formateur
  - AdminDashboardSerializer     : vue d'ensemble administrateur

AMBIGUÏTÉ : Pourquoi trois serializers séparés ?
  - Chaque rôle a des métriques totalement différentes
  - Un serializer unique avec des champs conditionnels serait illisible
  - La séparation facilite les tests et la maintenance
"""

from rest_framework import serializers


class StudentDashboardSerializer(serializers.Serializer):
    """
    Données du tableau de bord d'un apprenant.

    Champs retournés :
      - total_enrollments  : nombre de formations suivies
      - active_enrollments : formations en cours
      - completed_enrollments : formations terminées
      - certificates_count : nombre de certificats obtenus
      - current_progress   : liste des formations en cours avec progression
      - recent_activity    : dernières leçons accédées
    """

    total_enrollments = serializers.IntegerField()
    active_enrollments = serializers.IntegerField()
    completed_enrollments = serializers.IntegerField()
    certificates_count = serializers.IntegerField()
    current_progress = serializers.ListField(child=serializers.DictField())
    recent_activity = serializers.ListField(child=serializers.DictField())


class FormateurDashboardSerializer(serializers.Serializer):
    """
    Données du tableau de bord d'un formateur.

    Champs retournés :
      - total_formations     : nombre de formations créées
      - published_formations : formations publiées
      - total_students       : nombre d'apprenants uniques
      - total_revenue        : revenu total (formations payantes)
      - formations_stats     : liste des formations avec nb d'inscrits
      - recent_enrollments   : dernières inscriptions à ses formations
    """

    total_formations = serializers.IntegerField()
    published_formations = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    formations_stats = serializers.ListField(child=serializers.DictField())
    recent_enrollments = serializers.ListField(child=serializers.DictField())


class AdminDashboardSerializer(serializers.Serializer):
    """
    Données du tableau de bord administrateur.

    Champs retournés :
      - total_users        : nombre total d'utilisateurs
      - total_apprenants   : apprenants
      - total_formateurs   : formateurs
      - total_formations   : formations totales
      - published_formations : formations publiées
      - total_enrollments  : inscriptions totales
      - total_revenue      : revenu total de la plateforme
      - certificates_issued: certificats délivrés
      - recent_users       : derniers utilisateurs inscrits
      - recent_activity    : activité récente (inscriptions, terminaisons)
    """

    total_users = serializers.IntegerField()
    total_apprenants = serializers.IntegerField()
    total_formateurs = serializers.IntegerField()
    total_formations = serializers.IntegerField()
    published_formations = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    certificates_issued = serializers.IntegerField()
    recent_users = serializers.ListField(child=serializers.DictField())
    recent_activity = serializers.ListField(child=serializers.DictField())
