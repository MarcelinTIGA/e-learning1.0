"""
Serializers pour l'app 'courses'.

Un serializer convertit un objet Python/Django en JSON (pour la réponse API)
et valide les données JSON reçues (pour les requêtes POST/PATCH).

On utilise deux niveaux de détail pour les formations :
  - FormationListSerializer : version légère pour le catalogue (liste de formations)
  - FormationDetailSerializer : version complète avec modules et leçons imbriqués
"""

from rest_framework import serializers

from .models import Category, Formation, Lesson, Module


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer pour les catégories.
    Utilisé à la fois pour la lecture et la création/modification.
    """

    class Meta:
        model = Category
        # 'slug' est en lecture seule : il est auto-généré depuis le nom
        fields = ('id', 'name', 'slug', 'description')
        read_only_fields = ('slug',)


class LessonSerializer(serializers.ModelSerializer):
    """
    Serializer pour les leçons.
    Utilisé en lecture seule dans le détail d'un module (imbriqué).
    """

    class Meta:
        model = Lesson
        fields = (
            'id', 'titre', 'content_type',
            'video_url', 'pdf_file', 'text_content',
            'order', 'is_preview', 'duration_minutes',
        )
        # 'module' n'est pas inclus ici : on le connaît déjà via le contexte parent


class LessonWriteSerializer(serializers.ModelSerializer):
    """
    Serializer utilisé pour la CRÉATION et la MODIFICATION d'une leçon.
    Inclut 'module' pour permettre l'assignation lors de la création.
    """

    class Meta:
        model = Lesson
        fields = (
            'id', 'module', 'titre', 'content_type',
            'video_url', 'pdf_file', 'text_content',
            'order', 'is_preview', 'duration_minutes',
        )

    def validate(self, attrs):
        """
        Validation croisée : s'assure que le champ de contenu correct est rempli.
        Par exemple, une leçon de type 'video' doit avoir une video_url.
        """
        content_type = attrs.get('content_type', Lesson.ContentType.VIDEO)

        if content_type == Lesson.ContentType.VIDEO and not attrs.get('video_url'):
            raise serializers.ValidationError(
                {'video_url': "Une URL vidéo est requise pour ce type de leçon."}
            )
        if content_type == Lesson.ContentType.PDF and not attrs.get('pdf_file'):
            raise serializers.ValidationError(
                {'pdf_file': "Un fichier PDF est requis pour ce type de leçon."}
            )
        if content_type == Lesson.ContentType.TEXT and not attrs.get('text_content'):
            raise serializers.ValidationError(
                {'text_content': "Un contenu texte est requis pour ce type de leçon."}
            )
        return attrs


class ModuleSerializer(serializers.ModelSerializer):
    """
    Serializer pour les modules.
    Inclut les leçons imbriquées (lecture seule).
    La liste des leçons est incluse dans la réponse détaillée d'un module.
    """

    # many=True : une liste de leçons
    # read_only=True : on ne crée pas de leçons via ce serializer (voir LessonWriteSerializer)
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ('id', 'titre', 'description', 'order', 'lessons')
        # 'formation' n'est pas inclus ici : il est défini par l'URL


class ModuleWriteSerializer(serializers.ModelSerializer):
    """
    Serializer pour la CRÉATION et MODIFICATION d'un module.
    Inclut 'formation' pour l'assignation.
    """

    class Meta:
        model = Module
        fields = ('id', 'formation', 'titre', 'description', 'order')


class FormationListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour le CATALOGUE des formations.
    Utilisé dans la liste (GET /api/courses/) pour éviter de charger
    tous les modules et leçons de chaque formation.
    """

    # SerializerMethodField : champ calculé dynamiquement (appelle get_<nom_du_champ>)
    nb_modules = serializers.SerializerMethodField()
    nb_apprenants = serializers.SerializerMethodField()

    # StringRelatedField : affiche le __str__ de la catégorie (le nom) au lieu de l'ID
    categorie = serializers.StringRelatedField()

    # Nom du formateur (lecture seule, affiché comme string)
    formateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = Formation
        fields = (
            'id', 'titre', 'description', 'image', 'prix',
            'niveau', 'is_published', 'categorie', 'formateur_nom',
            'nb_modules', 'nb_apprenants', 'created_at',
        )

    def get_nb_modules(self, obj):
        """Retourne le nombre de modules de cette formation."""
        return obj.modules.count()

    def get_nb_apprenants(self, obj):
        """
        Retourne le nombre d'apprenants inscrits et ayant payé.
        On vérifie le statut 'active' pour ne compter que les inscriptions valides.
        """
        # .filter sur la relation inverse 'enrollments' (définie dans le modèle Enrollment)
        # Si l'app enrollments n'est pas encore créée, on retourne 0
        try:
            return obj.enrollments.filter(status='active').count()
        except Exception:
            return 0

    def get_formateur_nom(self, obj):
        """Retourne le nom complet du formateur."""
        return obj.formateur.full_name


class FormationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le DÉTAIL d'une formation.
    Inclut les modules avec leurs leçons (lecture seule).
    Utilisé dans GET /api/courses/{id}/
    """

    modules = ModuleSerializer(many=True, read_only=True)
    categorie = CategorySerializer(read_only=True)
    formateur_nom = serializers.SerializerMethodField()
    nb_apprenants = serializers.SerializerMethodField()

    class Meta:
        model = Formation
        fields = (
            'id', 'titre', 'description', 'image', 'prix',
            'niveau', 'is_published', 'categorie', 'formateur_nom',
            'modules', 'nb_apprenants', 'created_at', 'updated_at',
        )

    def get_formateur_nom(self, obj):
        return obj.formateur.full_name

    def get_nb_apprenants(self, obj):
        try:
            return obj.enrollments.filter(status='active').count()
        except Exception:
            return 0


class FormationWriteSerializer(serializers.ModelSerializer):
    """
    Serializer pour la CRÉATION et MODIFICATION d'une formation.
    Le champ 'formateur' est automatiquement rempli avec l'utilisateur connecté
    (voir la méthode perform_create dans les views).
    """

    class Meta:
        model = Formation
        fields = (
            'id', 'titre', 'description', 'image', 'prix',
            'niveau', 'is_published', 'categorie',
        )
        # 'formateur' est exclu : il sera assigné dans la view via perform_create()
