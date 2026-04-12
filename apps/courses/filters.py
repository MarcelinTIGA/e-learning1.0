"""
Filtres personnalisés pour les formations (catalogue).

Utilisé par CatalogueView via filterset_class = FormationFilter.
Permet de filtrer par :
  - niveau (debutant, intermediaire, avance)
  - prix_min / prix_max
  - categorie (slug ou ID)
"""

import django_filters

from .models import Formation


class FormationFilter(django_filters.FilterSet):
    """Filtres appliqués aux formations dans le catalogue."""

    niveau = django_filters.CharFilter(field_name='niveau', lookup_expr='exact')
    prix_min = django_filters.NumberFilter(field_name='prix', lookup_expr='gte')
    prix_max = django_filters.NumberFilter(field_name='prix', lookup_expr='lte')
    categorie = django_filters.CharFilter(field_name='categorie__slug', lookup_expr='exact')

    class Meta:
        model = Formation
        fields = ['niveau', 'prix_min', 'prix_max', 'categorie']
