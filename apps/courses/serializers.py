"""
Serializers pour l'app 'courses'.

Organisation :
  - CategorySerializer       : lecture/écriture catégorie
  - FormationListSerializer  : affichage léger dans les listes
  - FormationDetailSerializer : détail complet avec modules + leçons
  - FormationWriteSerializer : création/modification
  - ModuleSerializer         : lecture module
  - ModuleWriteSerializer    : écriture module
  - LessonSerializer         : lecture leçon
  - LessonWriteSerializer    : écriture leçon
"""

from rest_framework import serializers

from .models import Category, Formation, Lesson, Module


# ─────────────────────────────────────────────
# CATEGORY
# ─────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    """Serializer complet pour les catégories."""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']
        read_only_fields = ['slug']


# ─────────────────────────────────────────────
# LESSON
# ─────────────────────────────────────────────

class LessonSerializer(serializers.ModelSerializer):
    """Lecture d'une leçon."""

    class Meta:
        model = Lesson
        fields = [
            'id', 'titre', 'content_type', 'video_url',
            'pdf_file', 'text_content', 'order',
            'is_preview', 'duration_minutes',
        ]
        read_only_fields = ['id']


class LessonWriteSerializer(serializers.ModelSerializer):
    """Création/modification d'une leçon."""

    class Meta:
        model = Lesson
        fields = [
            'id', 'titre', 'content_type', 'video_url',
            'pdf_file', 'text_content', 'order',
            'is_preview', 'duration_minutes',
        ]

    def validate(self, attrs):
        """Validation croisée selon le type de contenu."""
        content_type = attrs.get('content_type')

        if content_type == Lesson.ContentType.VIDEO and not attrs.get('video_url'):
            raise serializers.ValidationError(
                {"video_url": "Une leçon vidéo nécessite une URL valide."}
            )
        if content_type == Lesson.ContentType.PDF and not attrs.get('pdf_file'):
            raise serializers.ValidationError(
                {"pdf_file": "Une leçon PDF nécessite un fichier."}
            )
        if content_type == Lesson.ContentType.TEXT and not attrs.get('text_content'):
            raise serializers.ValidationError(
                {"text_content": "Une leçon texte nécessite du contenu."}
            )
        return attrs


# ─────────────────────────────────────────────
# MODULE
# ─────────────────────────────────────────────

class ModuleSerializer(serializers.ModelSerializer):
    """Lecture d'un module avec ses leçons."""

    lessons = LessonSerializer(many=True, read_only=True)
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'titre', 'description', 'order', 'lessons', 'lessons_count']
        read_only_fields = ['id']

    def get_lessons_count(self, obj):
        return obj.lessons.count() if hasattr(obj, 'lessons') else 0


class ModuleWriteSerializer(serializers.ModelSerializer):
    """Création/modification d'un module."""

    class Meta:
        model = Module
        fields = ['id', 'titre', 'description', 'order']

    def validate_order(self, value):
        if value < 1:
            raise serializers.ValidationError("L'ordre doit être >= 1.")
        return value


# ─────────────────────────────────────────────
# FORMATION
# ─────────────────────────────────────────────

class FormationListSerializer(serializers.ModelSerializer):
    """Affichage léger dans les listes (catalogue, gestion)."""

    formateur_nom = serializers.SerializerMethodField()
    categorie_nom = serializers.SerializerMethodField()
    modules_count = serializers.SerializerMethodField()

    class Meta:
        model = Formation
        fields = [
            'id', 'titre', 'description', 'image', 'prix',
            'niveau', 'is_published', 'formateur_nom',
            'categorie_nom', 'modules_count', 'created_at',
            'is_free',
        ]
        read_only_fields = ['id', 'is_free', 'created_at']

    def get_formateur_nom(self, obj):
        return obj.formateur.full_name if obj.formateur else None

    def get_categorie_nom(self, obj):
        return obj.categorie.name if obj.categorie else None

    def get_modules_count(self, obj):
        return obj.modules.count() if hasattr(obj, 'modules') else 0


class FormationDetailSerializer(serializers.ModelSerializer):
    """Détail complet d'une formation avec modules et leçons."""

    formateur = serializers.SerializerMethodField()
    categorie = CategorySerializer(read_only=True)
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Formation
        fields = [
            'id', 'titre', 'description', 'image', 'prix',
            'niveau', 'is_published', 'formateur', 'categorie',
            'modules', 'created_at', 'updated_at', 'is_free',
        ]
        read_only_fields = ['id', 'is_free', 'created_at', 'updated_at']

    def get_formateur(self, obj):
        if not obj.formateur:
            return None
        return {
            'id': obj.formateur.id,
            'email': obj.formateur.email,
            'full_name': obj.formateur.full_name,
        }


class FormationWriteSerializer(serializers.ModelSerializer):
    """Création/modification d'une formation."""

    class Meta:
        model = Formation
        fields = [
            'id', 'titre', 'description', 'image', 'prix',
            'niveau', 'is_published', 'categorie',
        ]
        read_only_fields = ['id']

    def validate_prix(self, value):
        if value < 0:
            raise serializers.ValidationError("Le prix ne peut pas être négatif.")
        return value
