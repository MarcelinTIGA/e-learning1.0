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
    total_enrollments     = serializers.IntegerField()
    formations_en_cours   = serializers.IntegerField()
    formations_terminees  = serializers.IntegerField()
    certificats_obtenus   = serializers.IntegerField()
    quiz_passes           = serializers.IntegerField()
    current_progress      = serializers.ListField(child=serializers.DictField())
    recent_activity       = serializers.ListField(child=serializers.DictField())


class FormateurDashboardSerializer(serializers.Serializer):
    total_formations    = serializers.IntegerField()
    published_formations = serializers.IntegerField()
    total_apprenants    = serializers.IntegerField()
    total_revenus       = serializers.FloatField()
    taux_completion     = serializers.FloatField()
    formations          = serializers.ListField(child=serializers.DictField())
    recent_enrollments  = serializers.ListField(child=serializers.DictField())


class AdminDashboardSerializer(serializers.Serializer):
    total_users          = serializers.IntegerField()
    total_apprenants     = serializers.IntegerField()
    total_formateurs     = serializers.IntegerField()
    total_formations     = serializers.IntegerField()
    published_formations = serializers.IntegerField()
    total_enrollments    = serializers.IntegerField()
    total_revenus        = serializers.FloatField()
    certificates_issued  = serializers.IntegerField()
    recent_users         = serializers.ListField(child=serializers.DictField())
    recent_enrollments   = serializers.ListField(child=serializers.DictField())
