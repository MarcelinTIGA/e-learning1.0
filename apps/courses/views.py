"""
Views pour l'app 'courses'.

Organisation des endpoints :
  - CatalogueView       : GET  /api/courses/              — Liste publique des formations publiées
  - FormationDetailView : GET  /api/courses/{id}/         — Détail d'une formation (avec modules)
  - FormationListCreateView : GET/POST /api/courses/manage/   — Gestion des formations (formateur)
  - FormationUpdateView : PUT/PATCH/DELETE /api/courses/manage/{id}/
  - CategoryListCreateView  : GET/POST /api/courses/categories/
  - CategoryDetailView      : GET/PUT/PATCH/DELETE /api/courses/categories/{id}/
  - ModuleListCreateView    : GET/POST /api/courses/{formation_id}/modules/
  - ModuleDetailView        : GET/PUT/PATCH/DELETE /api/courses/modules/{id}/
  - LessonListCreateView    : GET/POST /api/courses/modules/{module_id}/lessons/
  - LessonDetailView        : GET/PUT/PATCH/DELETE /api/courses/lessons/{id}/
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.users.permissions import IsAdministrateur, IsFormateurOrAdmin

from .filters import FormationFilter
from .models import Category, Formation, Lesson, Module
from .permissions import IsFormateurOwnerOrAdmin, IsPublishedOrOwnerOrAdmin
from .serializers import (
    CategorySerializer,
    FormationDetailSerializer,
    FormationListSerializer,
    FormationWriteSerializer,
    LessonSerializer,
    LessonWriteSerializer,
    ModuleSerializer,
    ModuleWriteSerializer,
)


# ─────────────────────────────────────────────
# CATALOGUE PUBLIC
# ─────────────────────────────────────────────

class CatalogueView(generics.ListAPIView):
    """
    GET /api/courses/
    Catalogue public des formations PUBLIÉES.
    Accessible sans authentification.
    Supporte la recherche et les filtres (prix, niveau, catégorie).
    """

    # AllowAny : n'importe qui peut voir le catalogue, même sans compte
    permission_classes = [permissions.AllowAny]
    serializer_class = FormationListSerializer

    # filterset_class : classe de filtres personnalisés (voir filters.py)
    filterset_class = FormationFilter

    # search_fields : champs sur lesquels la recherche textuelle (?search=python) s'applique
    search_fields = ['titre', 'description', 'formateur__first_name', 'formateur__last_name']

    # ordering_fields : permet de trier via ?ordering=prix ou ?ordering=-created_at
    ordering_fields = ['prix', 'created_at', 'titre']

    def get_queryset(self):
        """
        Retourne uniquement les formations publiées, avec les relations préchargées.
        select_related() évite les requêtes SQL supplémentaires pour chaque formation.
        """
        return (
            Formation.objects
            .filter(is_published=True)
            # select_related : charge formateur et catégorie en une seule requête SQL (JOIN)
            .select_related('formateur', 'categorie')
            # prefetch_related : charge les modules en une requête séparée (évite N+1 queries)
            .prefetch_related('modules')
        )


class FormationPublicDetailView(generics.RetrieveAPIView):
    """
    GET /api/courses/{id}/
    Détail complet d'une formation avec ses modules et leçons.
    Les formations non publiées ne sont visibles que par leur formateur ou un admin.
    """

    permission_classes = [permissions.AllowAny, IsPublishedOrOwnerOrAdmin]
    serializer_class = FormationDetailSerializer

    def get_queryset(self):
        return (
            Formation.objects
            .select_related('formateur', 'categorie')
            # Charge modules → leçons en cascade (évite de nombreuses requêtes SQL)
            .prefetch_related('modules__lessons')
        )

    def get_object(self):
        """
        Surcharge pour appliquer la permission IsPublishedOrOwnerOrAdmin.
        check_object_permissions déclenche has_object_permission de cette permission.
        """
        obj = super().get_object()
        # Vérifie les permissions au niveau de l'objet
        for permission in self.get_permissions():
            if hasattr(permission, 'has_object_permission'):
                if not permission.has_object_permission(self.request, self, obj):
                    self.permission_denied(self.request)
        return obj


# ─────────────────────────────────────────────
# GESTION DES FORMATIONS (formateur)
# ─────────────────────────────────────────────

class FormationManageListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/courses/manage/  — Liste des formations du formateur connecté
    POST /api/courses/manage/  — Créer une nouvelle formation
    Réservé aux formateurs et administrateurs.
    """

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        """
        Retourne le bon serializer selon la méthode HTTP :
        - GET  → FormationListSerializer (léger, pour la liste)
        - POST → FormationWriteSerializer (complet, pour la création)
        """
        if self.request.method == 'POST':
            return FormationWriteSerializer
        return FormationListSerializer

    def get_queryset(self):
        """
        Un formateur ne voit que SES formations.
        Un administrateur voit toutes les formations.
        """
        user = self.request.user
        if user.is_administrateur:
            return Formation.objects.select_related('formateur', 'categorie').all()
        # Le formateur ne voit que ses propres formations
        return Formation.objects.filter(formateur=user).select_related('categorie')

    def perform_create(self, serializer):
        """
        Appelée automatiquement par DRF lors d'un POST.
        On injecte le formateur = l'utilisateur connecté.
        Ainsi le champ 'formateur' n'est pas requis dans la requête.
        """
        serializer.save(formateur=self.request.user)


class FormationManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/courses/manage/{id}/ — Voir sa formation
    PUT    /api/courses/manage/{id}/ — Modifier entièrement
    PATCH  /api/courses/manage/{id}/ — Modifier partiellement
    DELETE /api/courses/manage/{id}/ — Supprimer
    Seul le formateur propriétaire ou un admin peut modifier/supprimer.
    """

    permission_classes = [IsFormateurOrAdmin, IsFormateurOwnerOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return FormationWriteSerializer
        return FormationDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_administrateur:
            return Formation.objects.select_related('formateur', 'categorie').prefetch_related('modules__lessons')
        return Formation.objects.filter(formateur=user).select_related('categorie').prefetch_related('modules__lessons')


# ─────────────────────────────────────────────
# CATÉGORIES
# ─────────────────────────────────────────────

class CategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/courses/categories/ — Liste toutes les catégories (public)
    POST /api/courses/categories/ — Créer une catégorie (admin uniquement)
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        """
        Permissions dynamiques selon la méthode :
        - GET  : AllowAny (tout le monde peut voir les catégories)
        - POST : IsAdministrateur (seul l'admin peut créer)
        """
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdministrateur()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/courses/categories/{id}/ — Voir une catégorie (public)
    PUT/PATCH/DELETE : réservé aux administrateurs
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdministrateur()]


# ─────────────────────────────────────────────
# MODULES
# ─────────────────────────────────────────────

class ModuleListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/courses/{formation_pk}/modules/ — Lister les modules d'une formation
    POST /api/courses/{formation_pk}/modules/ — Ajouter un module
    """

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ModuleWriteSerializer
        return ModuleSerializer

    def get_queryset(self):
        """
        Filtre les modules par la formation passée dans l'URL.
        formation_pk est extrait de l'URL par le routeur (voir urls.py).
        """
        formation_pk = self.kwargs.get('formation_pk')
        return Module.objects.filter(formation_id=formation_pk).prefetch_related('lessons')

    def perform_create(self, serializer):
        """
        Vérifie que l'utilisateur est bien le formateur de la formation parente
        avant de créer le module.
        """
        formation_pk = self.kwargs.get('formation_pk')
        try:
            formation = Formation.objects.get(pk=formation_pk)
        except Formation.DoesNotExist:
            return Response({'detail': "Formation introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Vérification de la propriété : seul le propriétaire ou un admin peut ajouter un module
        if not self.request.user.is_administrateur and formation.formateur != self.request.user:
            self.permission_denied(self.request, message="Vous n'êtes pas le formateur de cette formation.")

        serializer.save(formation=formation)


class ModuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/courses/modules/{id}/ — Détail d'un module (avec ses leçons)
    PUT/PATCH/DELETE : formateur propriétaire ou admin
    """

    queryset = Module.objects.select_related('formation').prefetch_related('lessons')
    permission_classes = [IsFormateurOrAdmin, IsFormateurOwnerOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ModuleWriteSerializer
        return ModuleSerializer


# ─────────────────────────────────────────────
# LEÇONS
# ─────────────────────────────────────────────

class LessonListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/courses/modules/{module_pk}/lessons/ — Lister les leçons d'un module
    POST /api/courses/modules/{module_pk}/lessons/ — Ajouter une leçon
    """

    permission_classes = [IsFormateurOrAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LessonWriteSerializer
        return LessonSerializer

    def get_queryset(self):
        """Filtre les leçons par le module passé dans l'URL."""
        module_pk = self.kwargs.get('module_pk')
        return Lesson.objects.filter(module_id=module_pk)

    def perform_create(self, serializer):
        """
        Vérifie que l'utilisateur est bien le formateur du module (via formation)
        avant d'ajouter la leçon.
        """
        module_pk = self.kwargs.get('module_pk')
        try:
            module = Module.objects.select_related('formation').get(pk=module_pk)
        except Module.DoesNotExist:
            self.permission_denied(self.request, message="Module introuvable.")

        if not self.request.user.is_administrateur and module.formation.formateur != self.request.user:
            self.permission_denied(self.request, message="Vous n'êtes pas le formateur de ce module.")

        serializer.save(module=module)


class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/courses/lessons/{id}/ — Détail d'une leçon
    PUT/PATCH/DELETE : formateur propriétaire ou admin
    """

    queryset = Lesson.objects.select_related('module__formation')
    permission_classes = [IsFormateurOrAdmin, IsFormateurOwnerOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return LessonWriteSerializer
        return LessonSerializer
