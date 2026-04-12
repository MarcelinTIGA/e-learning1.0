"""
Configuration du panel d'administration Django pour l'app 'courses'.

Le panel admin (/admin/) permet aux administrateurs de gérer les données
directement via une interface web sans passer par l'API.
"""

from django.contrib import admin

from .models import Category, Formation, Lesson, Module


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Administration des catégories de formations."""

    list_display = ('name', 'slug', 'description')
    # prepopulated_fields : remplit automatiquement le slug depuis le nom dans l'interface admin
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ModuleInline(admin.TabularInline):
    """
    Inline : permet de voir et modifier les modules directement
    depuis la page de détail d'une formation dans l'admin.
    TabularInline = affichage en tableau (ligne par module).
    """

    model = Module
    # extra=0 : ne montre pas de formulaires vides supplémentaires par défaut
    extra = 0
    fields = ('titre', 'order', 'description')
    ordering = ('order',)


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    """Administration des formations."""

    # Colonnes affichées dans la liste des formations
    list_display = ('titre', 'formateur', 'categorie', 'niveau', 'prix', 'is_published', 'created_at')

    # Filtres dans la barre latérale droite
    list_filter = ('is_published', 'niveau', 'categorie')

    # Champs de recherche
    search_fields = ('titre', 'description', 'formateur__email', 'formateur__first_name')

    # Modules affichés dans la page de détail de la formation
    inlines = [ModuleInline]

    # Champs affichés dans le formulaire de création/modification
    fieldsets = (
        (None, {'fields': ('titre', 'description', 'image')}),
        ('Informations', {'fields': ('formateur', 'categorie', 'niveau', 'prix')}),
        ('Publication', {'fields': ('is_published',)}),
    )

    # Permet de modifier is_published directement depuis la liste (sans ouvrir le formulaire)
    list_editable = ('is_published',)


class LessonInline(admin.TabularInline):
    """Inline pour voir les leçons dans la page de détail d'un module."""

    model = Lesson
    extra = 0
    fields = ('titre', 'content_type', 'order', 'is_preview', 'duration_minutes')
    ordering = ('order',)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """Administration des modules."""

    list_display = ('titre', 'formation', 'order')
    list_filter = ('formation',)
    search_fields = ('titre', 'formation__titre')
    inlines = [LessonInline]
    ordering = ('formation', 'order')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """Administration des leçons."""

    list_display = ('titre', 'module', 'content_type', 'order', 'is_preview', 'duration_minutes')
    list_filter = ('content_type', 'is_preview')
    search_fields = ('titre', 'module__titre')
    ordering = ('module', 'order')
