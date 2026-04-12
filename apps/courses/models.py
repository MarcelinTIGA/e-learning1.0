"""
Modèles de l'app 'courses' — Structure pédagogique de la plateforme.

Hiérarchie :
    Category
        └── Formation  (un cours complet, ex: "Python pour débutants")
                └── Module  (chapitre, ex: "Les bases de Python")
                        └── Lesson  (leçon individuelle, ex: "Les variables")

Chaque Formation appartient à un formateur et peut contenir plusieurs modules.
Chaque Module contient plusieurs leçons ordonnées.
"""

from django.conf import settings  # Pour référencer AUTH_USER_MODEL de façon sûre
from django.db import models
from django.utils.text import slugify  # Convertit un texte en slug URL-compatible


class Category(models.Model):
    """
    Catégorie de formation (ex: Informatique, Design, Marketing...).
    Sert à organiser et filtrer les formations dans le catalogue.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")

    # slug : version URL-friendly du nom (ex: "Développement Web" → "developpement-web")
    # blank=True car on le génère automatiquement dans save()
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        db_table = 'categories'
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['name']  # Triées alphabétiquement par défaut

    def save(self, *args, **kwargs):
        # Auto-génération du slug à partir du nom si non fourni
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Formation(models.Model):
    """
    Un cours complet proposé sur la plateforme (équivalent d'un cours Udemy).
    Appartient à un formateur, est lié à une catégorie.
    """

    class Level(models.TextChoices):
        """Niveaux de difficulté disponibles pour une formation."""
        DEBUTANT = 'debutant', 'Débutant'
        INTERMEDIAIRE = 'intermediaire', 'Intermédiaire'
        AVANCE = 'avance', 'Avancé'

    # Le formateur qui a créé cette formation (clé étrangère vers User)
    # on_delete=models.CASCADE : si le formateur est supprimé, ses formations aussi
    formateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='formations',  # permet d'écrire user.formations.all()
        verbose_name="Formateur",
    )

    # Catégorie de la formation (optionnelle : SET_NULL garde la formation si la catégorie est supprimée)
    categorie = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='formations',
        verbose_name="Catégorie",
    )

    titre = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(verbose_name="Description")

    # Image de couverture de la formation (optionnelle)
    image = models.ImageField(upload_to='formations/', blank=True, null=True, verbose_name="Image")

    # Prix en Francs CFA (devise locale)
    prix = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Prix (XAF)",
    )

    niveau = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.DEBUTANT,
        verbose_name="Niveau",
    )

    # is_published : contrôle la visibilité dans le catalogue public
    # Une formation non publiée n'est visible que par son formateur
    is_published = models.BooleanField(default=False, verbose_name="Publiée")

    created_at = models.DateTimeField(auto_now_add=True)  # Date de création (automatique)
    updated_at = models.DateTimeField(auto_now=True)       # Date de dernière modification (automatique)

    class Meta:
        db_table = 'formations'
        verbose_name = 'Formation'
        verbose_name_plural = 'Formations'
        ordering = ['-created_at']  # Les plus récentes en premier

    def __str__(self):
        return self.titre

    @property
    def is_free(self):
        """Retourne True si la formation est gratuite (prix = 0)."""
        return self.prix == 0


class Module(models.Model):
    """
    Un chapitre au sein d'une formation (ex: "Module 1 : Les bases").
    Les modules sont ordonnés par le champ 'order'.
    """

    # Chaque module appartient à une formation
    # on_delete=CASCADE : si la formation est supprimée, ses modules le sont aussi
    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name='modules',  # permet d'écrire formation.modules.all()
        verbose_name="Formation",
    )

    titre = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")

    # order : position du module dans la formation (1, 2, 3...)
    # Les apprenants doivent compléter les modules dans cet ordre
    order = models.PositiveIntegerField(default=1, verbose_name="Ordre")

    class Meta:
        db_table = 'modules'
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'
        ordering = ['order']  # Toujours triés par ordre croissant

        # Contrainte d'unicité : deux modules d'une même formation ne peuvent pas avoir le même ordre
        unique_together = [('formation', 'order')]

    def __str__(self):
        return f"{self.formation.titre} — Module {self.order} : {self.titre}"


class Lesson(models.Model):
    """
    Une leçon individuelle au sein d'un module.
    Peut être de type : vidéo, PDF, ou texte.
    Les leçons sont ordonnées et certaines peuvent être en prévisualisation gratuite.
    """

    class ContentType(models.TextChoices):
        """Types de contenu possibles pour une leçon."""
        VIDEO = 'video', 'Vidéo'
        PDF = 'pdf', 'PDF'
        TEXT = 'text', 'Texte'

    # Chaque leçon appartient à un module
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='lessons',  # permet d'écrire module.lessons.all()
        verbose_name="Module",
    )

    titre = models.CharField(max_length=200, verbose_name="Titre")

    content_type = models.CharField(
        max_length=10,
        choices=ContentType.choices,
        default=ContentType.VIDEO,
        verbose_name="Type de contenu",
    )

    # Champs de contenu — un seul utilisé selon le content_type
    video_url = models.URLField(
        blank=True,
        verbose_name="URL vidéo (YouTube/Vimeo)",
        help_text="Lien externe vers la vidéo (YouTube, Vimeo, etc.)",
    )
    pdf_file = models.FileField(
        upload_to='lessons/pdfs/',
        blank=True,
        null=True,
        verbose_name="Fichier PDF",
    )
    text_content = models.TextField(blank=True, verbose_name="Contenu texte")

    order = models.PositiveIntegerField(default=1, verbose_name="Ordre")

    # is_preview : si True, cette leçon est accessible sans être inscrit
    # Utile pour donner un aperçu de la formation aux visiteurs
    is_preview = models.BooleanField(
        default=False,
        verbose_name="Prévisualisation gratuite",
    )

    # Durée estimée en minutes (optionnel, pour informer l'apprenant)
    duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name="Durée (minutes)",
    )

    class Meta:
        db_table = 'lessons'
        verbose_name = 'Leçon'
        verbose_name_plural = 'Leçons'
        ordering = ['order']  # Toujours triées par ordre croissant

        # Deux leçons du même module ne peuvent pas avoir le même numéro d'ordre
        unique_together = [('module', 'order')]

    def __str__(self):
        return f"{self.module.titre} — Leçon {self.order} : {self.titre}"
