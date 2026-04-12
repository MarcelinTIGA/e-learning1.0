"""
Filtres personnalisés pour l'app 'courses'.

django-filter permet d'ajouter des paramètres de filtrage aux endpoints API.
Exemple d'utilisation dans l'URL :
    GET /api/courses/?prix_min=0&prix_max=5000&niveau=debutant&categorie=1

Ces filtres sont appliqués automatiquement par DjangoFilterBackend (configuré dans settings.py).
"""

import django_filters  # Bibliothèque de filtrage pour Django REST Framework

from .models import Formation


class FormationFilter(django_filters.FilterSet):
    """
    Filtre de recherche avancée pour les formations du catalogue.

    Paramètres URL disponibles :
        - prix_min  : prix minimum (ex: ?prix_min=1000)
        - prix_max  : prix maximum (ex: ?prix_max=10000)
        - niveau    : niveau de difficulté (ex: ?niveau=debutant)
        - categorie : ID de la catégorie (ex: ?categorie=3)
        - gratuit   : true/false pour filtrer les formations gratuites (ex: ?gratuit=true)
    """

    # NumberFilter : filtre numérique avec une comparaison spécifique
    # field_name='prix' : le champ du modèle sur lequel appliquer le filtre
    # lookup_expr='gte' : "greater than or equal" = supérieur ou égal (>=)
    prix_min = django_filters.NumberFilter(
        field_name='prix',
        lookup_expr='gte',
        label="Prix minimum",
    )

    # lookup_expr='lte' : "less than or equal" = inférieur ou égal (<=)
    prix_max = django_filters.NumberFilter(
        field_name='prix',
        lookup_expr='lte',
        label="Prix maximum",
    )

    # CharFilter : filtre textuel exact
    # lookup_expr='iexact' : comparaison insensible à la casse (Débutant = debutant)
    niveau = django_filters.CharFilter(
        field_name='niveau',
        lookup_expr='iexact',
        label="Niveau de difficulté",
    )

    # NumberFilter simple : filtre par ID de catégorie
    categorie = django_filters.NumberFilter(
        field_name='categorie__id',
        label="Catégorie (ID)",
    )

    # BooleanFilter : filtre pour les formations gratuites uniquement
    # Permet ?gratuit=true dans l'URL
    gratuit = django_filters.BooleanFilter(
        field_name='prix',
        lookup_expr='exact',
        label="Gratuit uniquement",
        method='filter_gratuit',  # Délègue à une méthode personnalisée ci-dessous
    )

    def filter_gratuit(self, queryset, name, value):
        """
        Filtre personnalisé pour les formations gratuites.
        Si value=True, retourne uniquement les formations avec prix=0.
        Si value=False, retourne uniquement les formations payantes (prix > 0).
        """
        if value:
            return queryset.filter(prix=0)
        return queryset.filter(prix__gt=0)  # __gt = "greater than" (>)

    class Meta:
        model = Formation
        # Champs filtrables directement par valeur exacte
        fields = ['prix_min', 'prix_max', 'niveau', 'categorie', 'gratuit']
