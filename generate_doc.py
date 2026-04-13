"""
Script de génération du document PDF de présentation du projet e-learning.
Destiné à un débutant en programmation.

Utilisation :
    source env/bin/activate
    python generate_doc.py
"""

import io
import os
import sys
from datetime import datetime

# Ajouter le chemin du projet pour importer reportlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'env', 'lib', 'python3.13', 'site-packages'))

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, HRFlowable, KeepTogether
)
from reportlab.lib.units import inch


# ─────────────────────────────────────────────
# COULEURS
# ─────────────────────────────────────────────
PRIMARY = HexColor('#1a3c6e')       # Bleu foncé
SECONDARY = HexColor('#2d6cb4')     # Bleu moyen
ACCENT = HexColor('#d4a017')        # Or
LIGHT_BG = HexColor('#f0f4f8')      # Gris-bleu clair
WHITE = HexColor('#ffffff')
DARK_TEXT = HexColor('#222222')
MEDIUM_TEXT = HexColor('#444444')
LIGHT_TEXT = HexColor('#666666')
BORDER = HexColor('#dde4eb')
CODE_BG = HexColor('#f5f5f5')
SUCCESS = HexColor('#28a745')
NOTE_BG = HexColor('#fff8e1')


def build_document():
    """Construit le document PDF complet."""

    output_path = os.path.join(os.path.dirname(__file__), 'DOCUMENTATION_PROJET.pdf')

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        title='Documentation Projet — Plateforme E-Learning',
        author='EFG Platform',
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # ── Styles personnalisés ──────────────────────────────────────
    styles.add(ParagraphStyle(
        'TitleCustom', parent=styles['Title'],
        fontName='Helvetica-Bold', fontSize=28, leading=36,
        textColor=PRIMARY, alignment=TA_CENTER,
        spaceAfter=6, spaceBefore=0,
    ))

    styles.add(ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=14, leading=20,
        textColor=SECONDARY, alignment=TA_CENTER,
        spaceAfter=20, spaceBefore=0,
    ))

    styles.add(ParagraphStyle(
        'H1', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=18, leading=26,
        textColor=PRIMARY, spaceBefore=24, spaceAfter=10,
        borderWidth=0, borderColor=PRIMARY, borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=14, leading=20,
        textColor=SECONDARY, spaceBefore=16, spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        'H3', parent=styles['Heading3'],
        fontName='Helvetica-Bold', fontSize=12, leading=16,
        textColor=DARK_TEXT, spaceBefore=12, spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10.5, leading=15,
        textColor=DARK_TEXT, alignment=TA_JUSTIFY,
        spaceBefore=2, spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        'BodyBold', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10.5, leading=15,
        textColor=DARK_TEXT, alignment=TA_JUSTIFY,
        spaceBefore=2, spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        'BodyItalic', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=10, leading=14,
        textColor=LIGHT_TEXT, alignment=TA_JUSTIFY,
        spaceBefore=2, spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        'CodeBlock', parent=styles['Normal'],
        fontName='Courier', fontSize=9.5, leading=14,
        textColor=DARK_TEXT, backColor=CODE_BG,
        borderWidth=1, borderColor=BORDER, borderPadding=6,
        spaceBefore=4, spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        'CodeInline', parent=styles['Normal'],
        fontName='Courier', fontSize=9.5, leading=13,
        textColor=HexColor('#c7254e'), backColor=CODE_BG,
        borderWidth=0, borderPadding=1,
    ))

    styles.add(ParagraphStyle(
        'NoteBlock', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=10, leading=14,
        textColor=MEDIUM_TEXT, backColor=NOTE_BG,
        borderWidth=1, borderColor=ACCENT, borderPadding=8,
        spaceBefore=6, spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        'ListItem', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10.5, leading=15,
        textColor=DARK_TEXT, leftIndent=20, bulletIndent=6,
        spaceBefore=1, spaceAfter=2,
    ))

    # ── Contenu du document ───────────────────────────────────────
    story = []

    # ═══════════════════════════════════════════════
    # PAGE DE COUVERTURE
    # ═══════════════════════════════════════════════
    story.append(Spacer(1, 40 * mm))

    # Ligne décorative
    story.append(HRFlowable(
        width="80%", thickness=2, color=ACCENT,
        spaceBefore=0, spaceAfter=20,
    ))

    story.append(Paragraph('Plateforme E-Learning', styles['TitleCustom']))
    story.append(Paragraph('Documentation Complète du Projet Backend', styles['Subtitle']))

    story.append(HRFlowable(
        width="80%", thickness=2, color=ACCENT,
        spaceBefore=10, spaceAfter=30,
    ))

    # Méta-informations
    meta_data = [
        ['Version', '1.0'],
        ['Date', datetime.now().strftime('%d %B %Y')],
        ['Framework', 'Django 6.0.4 + Django REST Framework'],
        ['Langage', 'Python 3.13.7'],
        ['Base de données', 'SQLite (dev) / PostgreSQL (prod)'],
        ['Auteur', 'EFG Platform'],
    ]
    meta_table = Table(meta_data, colWidths=[6 * cm, 10 * cm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), PRIMARY),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK_TEXT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, BORDER),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 20 * mm))

    story.append(Paragraph(
        '<i>Ce document explique en détail le fonctionnement du projet e-learning '
        'à destination des débutants en programmation.</i>',
        styles['NoteBlock'],
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # TABLE DES MATIÈRES
    # ═══════════════════════════════════════════════
    story.append(Paragraph('Table des Matières', styles['H1']))
    story.append(Spacer(1, 10))

    toc_items = [
        '1. Qu\'est-ce qu\'une application web ?',
        '   1.1 Client et Serveur',
        '   1.2 API REST',
        '   1.3 Base de données',
        '2. Présentation du Projet',
        '   2.1 Objectif',
        '   2.2 Rôles utilisateurs',
        '   2.3 Fonctionnalités principales',
        '3. Technologies Utilisées',
        '   3.1 Python',
        '   3.2 Django',
        '   3.3 Django REST Framework',
        '   3.4 JWT (JSON Web Tokens)',
        '   3.5 SQLite',
        '   3.6 Autres bibliothèques',
        '4. Architecture du Projet',
        '   4.1 Structure des fichiers',
        '   4.2 Les applications Django',
        '   4.3 Modèle de données (MVT)',
        '5. Guide pas à pas',
        '   5.1 Installer le projet',
        '   5.2 Lancer le serveur',
        '   5.3 Tester les endpoints',
        '6. Concepts Clés Expliqués',
        '   6.1 Authentification JWT',
        '   6.2 Sérialisation',
        '   6.3 Permissions',
        '   6.4 Migrations',
        '7. Lexique pour Débutants',
    ]

    for item in toc_items:
        indent = 15 if item.startswith('   ') else 6
        style = ParagraphStyle(
            'TOC', parent=styles['Normal'],
            fontName='Helvetica-Bold' if not item.startswith('   ') else 'Helvetica',
            fontSize=10.5 if not item.startswith('   ') else 10,
            leading=18,
            textColor=PRIMARY if not item.startswith('   ') else MEDIUM_TEXT,
            leftIndent=indent,
            spaceBefore=0, spaceAfter=0,
        )
        story.append(Paragraph(item, style))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # CHAPITRE 1 : QU'EST-CE QU'UNE APPLICATION WEB ?
    # ═══════════════════════════════════════════════
    story.append(Paragraph('1. Qu\'est-ce qu\'une application web ?', styles['H1']))

    story.append(Paragraph(
        'Une <b>application web</b> est un programme qui fonctionne sur Internet (ou sur un réseau local). '
        'Elle permet aux utilisateurs d\'interagir avec des données via un navigateur web (Chrome, Firefox, etc.) '
        'ou une application mobile.',
        styles['Body'],
    ))

    story.append(Paragraph(
        'Notre projet est un <b>backend API</b> : c\'est la partie invisible qui gère les données et la logique métier. '
        'Il n\'y a pas d\'interface graphique (frontend) dans ce projet — le backend est conçu pour être utilisé '
        'par un frontend séparé (application web React, application mobile Flutter, etc.).',
        styles['Body'],
    ))

    # 1.1 Client et Serveur
    story.append(Paragraph('1.1 Client et Serveur', styles['H2']))

    story.append(Paragraph(
        'Imaginez un restaurant :',
        styles['Body'],
    ))

    story.append(Paragraph(
        '• Le <b>client</b> (vous, le client au restaurant) envoie une commande (une requête).<br/>'
        '• Le <b>serveur</b> (le serveur du restaurant) reçoit la commande, la transmet en cuisine, '
        'et ramène le plat (la réponse).<br/>'
        '• La <b>cuisine</b> (la base de données) prépare les plats et stocke les ingrédients.',
        styles['Body'],
    ))

    story.append(Paragraph(
        'En informatique : le <b>client</b> (navigateur ou app mobile) envoie une <b>requête HTTP</b> '
        'au <b>serveur</b> (notre backend Django), qui lit/modifie les données dans la <b>base de données</b> '
        'et renvoie une <b>réponse HTTP</b> (généralement au format JSON).',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>Requête HTTP</b> : Un message envoyé du client vers le serveur. Exemple : "Donne-moi la liste des cours".<br/>'
        '<b>Réponse HTTP</b> : Le message retourné par le serveur. Exemple : "Voici la liste : [cours1, cours2, ...]".',
        styles['NoteBlock'],
    ))

    # 1.2 API REST
    story.append(Paragraph('1.2 API REST', styles['H2']))

    story.append(Paragraph(
        '<b>API</b> signifie <i>Application Programming Interface</i> (Interface de Programmation). '
        'C\'est un ensemble de "règles" qui permet à deux programmes de communiquer entre eux.',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>REST</b> est un style d\'architecture pour les API. Il repose sur des concepts simples :',
        styles['Body'],
    ))

    rest_items = [
        '<b>GET</b> : Lire des données (ex: voir la liste des cours)',
        '<b>POST</b> : Créer des données (ex: créer un nouveau cours)',
        '<b>PUT/PATCH</b> : Modifier des données (ex: changer le titre d\'un cours)',
        '<b>DELETE</b> : Supprimer des données (ex: supprimer un cours)',
    ]
    for item in rest_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    story.append(Paragraph(
        'Notre API expose des <b>endpoints</b> (points d\'accès), qui sont des URLs comme :',
        styles['Body'],
    ))

    story.append(Paragraph(
        'GET    /api/courses/           → Liste des cours<br/>'
        'POST   /api/courses/manage/    → Créer un cours<br/>'
        'GET    /api/courses/5/         → Détail du cours n°5<br/>'
        'POST   /api/auth/login/        → Se connecter<br/>'
        'GET    /api/dashboard/student/ → Tableau de bord apprenant',
        styles['CodeBlock'],
    ))

    # 1.3 Base de données
    story.append(Paragraph('1.3 Base de données', styles['H2']))

    story.append(Paragraph(
        'Une <b>base de données</b> est comme un gros classeur numérique qui stocke les informations '
        'de manière organisée. Dans notre projet :',
        styles['Body'],
    ))

    bd_items = [
        'Les <b>utilisateurs</b> (email, mot de passe, rôle)',
        'Les <b>formations</b> (titre, description, prix, niveau)',
        'Les <b>modules</b> et <b>leçons</b> qui composent chaque formation',
        'Les <b>inscriptions</b> (quel apprenant suit quelle formation)',
        'Les <b>certificats</b> (PDF de réussite)',
    ]
    for item in bd_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    story.append(Paragraph(
        'En développement, on utilise <b>SQLite</b> (un fichier local, simple). '
        'En production (sur Internet), on utiliserait <b>PostgreSQL</b> (plus puissant, plus sûr).',
        styles['Body'],
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # CHAPITRE 2 : PRÉSENTATION DU PROJET
    # ═══════════════════════════════════════════════
    story.append(Paragraph('2. Présentation du Projet', styles['H1']))

    story.append(Paragraph(
        'Ce projet est un <b>backend API pour une plateforme e-learning</b>. '
        'Il permet à trois types d\'utilisateurs (apprenant, formateur, administrateur) '
        'de gérer et suivre des formations en ligne.',
        styles['Body'],
    ))

    # 2.1 Objectif
    story.append(Paragraph('2.1 Objectif', styles['H2']))

    story.append(Paragraph(
        'L\'objectif est de créer une plateforme où :',
        styles['Body'],
    ))

    obj_items = [
        'Les <b>formateurs</b> peuvent créer des formations avec des modules et des leçons (vidéo, texte, PDF, quiz)',
        'Les <b>apprenants</b> peuvent s\'inscrire, suivre des formations, passer des quiz et obtenir des certificats',
        'Les <b>administrateurs</b> peuvent gérer les utilisateurs, les catégories et superviser la plateforme',
        'Le <b>paiement</b> se fait via Mobile Money (Orange Money, MTN MoMo)',
    ]
    for item in obj_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    # 2.2 Rôles
    story.append(Paragraph('2.2 Rôles Utilisateurs', styles['H2']))

    roles_data = [
        ['Apprenant', 'Suivre des formations, passer des quiz, obtenir des certificats'],
        ['Formateur', 'Créer et gérer ses formations, suivre les inscriptions'],
        ['Administrateur', 'Gérer toute la plateforme, les utilisateurs et les statistiques'],
    ]
    roles_table = Table(
        [['Rôle', 'Ce qu\'il peut faire']] + roles_data,
        colWidths=[3.5 * cm, 12 * cm],
    )
    roles_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BG),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(roles_table)

    # 2.3 Fonctionnalités
    story.append(Paragraph('2.3 Fonctionnalités Principales', styles['H2']))

    features = [
        ['Authentification', 'Inscription, connexion, déconnexion, réinitialisation mot de passe, OAuth (Google, Facebook)'],
        ['Catalogue', 'Liste des formations avec filtres (prix, niveau, catégorie) et recherche'],
        ['Gestion des cours', 'CRUD complet : formations → modules → leçons (vidéo, texte, PDF)'],
        ['Inscriptions', 'Gratuit (accès direct) ou payant (via Mobile Money)'],
        ['Progression', 'Suivi leçon par leçon, position vidéo, pourcentage global'],
        ['Quiz', 'QCM et Vrai/Faux, correction automatique, historique des tentatives'],
        ['Certificats', 'Génération PDF automatique à 100% de progression, code de vérification'],
        ['Dashboard', 'Statistiques par rôle (apprenant, formateur, admin)'],
    ]

    feat_table_data = [['Module', 'Description']] + features
    feat_table = Table(feat_table_data, colWidths=[3.5 * cm, 12 * cm])
    feat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(feat_table)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # CHAPITRE 3 : TECHNOLOGIES UTILISÉES
    # ═══════════════════════════════════════════════
    story.append(Paragraph('3. Technologies Utilisées', styles['H1']))

    # 3.1 Python
    story.append(Paragraph('3.1 Python', styles['H2']))

    story.append(Paragraph(
        '<b>Python</b> est un langage de programmation populaire, connu pour sa syntaxe claire et lisible. '
        'C\'est le langage principal de notre projet.',
        styles['Body'],
    ))

    story.append(Paragraph(
        'Pourquoi Python ?',
        styles['BodyBold'],
    ))

    python_items = [
        '<b>Simple à apprendre</b> : la syntaxe ressemble à de l\'anglais',
        '<b>Polyvalent</b> : web, data science, intelligence artificielle, automatisation',
        '<b>Grande communauté</b> : des milliers de bibliothèques gratuites',
        '<b>Version 3.13.7</b> : la dernière version stable, rapide et sécurisée',
    ]
    for item in python_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    story.append(Paragraph(
        '<b>Exemple de code Python :</b>',
        styles['BodyBold'],
    ))

    story.append(Paragraph(
        '# Créer un utilisateur<br/>'
        'user = User.objects.create_user(<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;email="jean@test.com",<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;password="MonMotDePasse123!",<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;first_name="Jean",<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;last_name="Dupont"<br/>'
        ')',
        styles['CodeBlock'],
    ))

    # 3.2 Django
    story.append(Paragraph('3.2 Django', styles['H2']))

    story.append(Paragraph(
        '<b>Django</b> est un framework web Python. Un "framework" est une boîte à outils qui fournit '
        'tout ce qu\'il faut pour créer une application web sans tout réinventer.',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>Analogue :</b> Si Python est le langage (comme le français), Django est un modèle de lettre '
        'pré-écrit. Vous n\'avez qu\'à remplir les blancs au lieu de rédiger depuis zéro.',
        styles['NoteBlock'],
    ))

    django_items = [
        '<b>ORM</b> (Object-Relational Mapping) : manipuler la base de données avec du Python au lieu de SQL',
        '<b>Admin automatique</b> : interface d\'administration générée automatiquement',
        '<b>Sécurité</b> : protection CSRF, XSS, injection SQL intégrée',
        '<b>Système d\'authentification</b> : gestion des utilisateurs et des sessions',
        '<b>Version 6.0.4</b> : dernière version, optimisée pour la performance',
    ]
    for item in django_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    story.append(Paragraph(
        '<b>Pattern MVT de Django :</b><br/>'
        'Django suit un modèle en 3 couches appelé <b>MVT</b> (Modèle — Vue — Template) :',
        styles['BodyBold'],
    ))

    mvt_items = [
        '<b>Modèle (Model)</b> : définit la structure des données (comme un formulaire avec des champs)',
        '<b>Vue (View)</b> : la logique — reçoit la requête, consulte le modèle, retourne une réponse',
        '<b>Template</b> : l\'affichage HTML (dans notre cas, on retourne du JSON, pas du HTML)',
    ]
    for item in mvt_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    # 3.3 DRF
    story.append(Paragraph('3.3 Django REST Framework (DRF)', styles['H2']))

    story.append(Paragraph(
        'Django est conçu pour servir des pages HTML. Mais notre projet est une <b>API</b> '
        '(on retourne du JSON, pas du HTML). <b>Django REST Framework</b> est une extension de Django '
        'qui facilite la création d\'APIs.',
        styles['Body'],
    ))

    drf_items = [
        '<b>Serializers</b> : convertissent les objets Python (modèles) en JSON et vice-versa',
        '<b>Views génériques</b> : des vues prêtes à l\'emploi (Lister, Créer, Lire, Modifier, Supprimer)',
        '<b>Permissions</b> : contrôler qui a accès à quoi',
        '<b>Pagination</b> : diviser les grandes listes en pages',
        '<b>Filtres</b> : permettre la recherche et le tri',
    ]
    for item in drf_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    story.append(Paragraph(
        '<b>Exemple de Serializer :</b>',
        styles['BodyBold'],
    ))

    story.append(Paragraph(
        'class FormationSerializer(serializers.ModelSerializer):<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;class Meta:<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;model = Formation<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;fields = [\'id\', \'titre\', \'description\', \'prix\']',
        styles['CodeBlock'],
    ))

    # 3.4 JWT
    story.append(Paragraph('3.4 JWT (JSON Web Tokens)', styles['H2']))

    story.append(Paragraph(
        '<b>JWT</b> est un système d\'authentification moderne. Quand un utilisateur se connecte '
        'avec son email et mot de passe, le serveur lui donne un <b>token</b> (jeton). '
        'Ce token est comme un badge d\'accès : à chaque requête, l\'utilisateur le présente '
        'pour prouver son identité.',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>Analogue :</b> Le JWT est comme un bracelet d\'accès dans un festival. '
        'Vous montrez votre identité une fois à l\'entrée, on vous donne un bracelet. '
        'Ensuite, vous montrez simplement le bracelet pour accéder aux zones.',
        styles['NoteBlock'],
    ))

    jwt_items = [
        '<b>Access Token</b> : valide 30 minutes — permet d\'accéder aux ressources',
        '<b>Refresh Token</b> : valide 7 jours — permet de demander un nouveau Access Token',
        '<b>Rotation</b> : à chaque rafraîchissement, un nouveau Refresh Token est généré',
        '<b>Blacklist</b> : les anciens tokens sont mis sur liste noire (déconnexion)',
    ]
    for item in jwt_items:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    story.append(Paragraph(
        '<b>Exemple de requête authentifiée :</b>',
        styles['BodyBold'],
    ))

    story.append(Paragraph(
        'GET /api/courses/manage/<br/>'
        'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        styles['CodeBlock'],
    ))

    # 3.5 SQLite
    story.append(Paragraph('3.5 SQLite', styles['H2']))

    story.append(Paragraph(
        '<b>SQLite</b> est une base de données légère, stockée dans un seul fichier (<b>db.sqlite3</b>). '
        'Elle est parfaite pour le développement car elle ne nécessite aucune installation.',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>En production</b>, on utiliserait <b>PostgreSQL</b>, une base de données plus robuste '
        'qui supporte plus d\'utilisateurs simultanés et offre de meilleures performances.',
        styles['Body'],
    ))

    # 3.6 Autres bibliothèques
    story.append(Paragraph('3.6 Autres Bibliothèques', styles['H2']))

    libs_data = [
        ['django-cors-headers', 'Permet au frontend (sur un autre serveur) d\'appeler l\'API'],
        ['django-allauth', 'Gère l\'inscription via Google et Facebook'],
        ['dj-rest-auth', 'Endpoints prêts à l\'emploi pour login/register/logout'],
        ['django-filter', 'Permet de filtrer les résultats (par prix, niveau, etc.)'],
        ['Pillow', 'Manipule les images (avatars, couvertures de formations)'],
        ['reportlab', 'Génère les certificats PDF'],
        ['python-decouple', 'Gère les variables d\'environnement (.env)'],
        ['SimpleJWT', 'Implémentation JWT pour Django REST Framework'],
    ]

    libs_table = Table(
        [['Bibliothèque', 'À quoi ça sert']] + libs_data,
        colWidths=[4.5 * cm, 11 * cm],
    )
    libs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(libs_table)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # CHAPITRE 4 : ARCHITECTURE DU PROJET
    # ═══════════════════════════════════════════════
    story.append(Paragraph('4. Architecture du Projet', styles['H1']))

    story.append(Paragraph(
        'Le projet est organisé en <b>applications Django</b> modulaires. '
        'Chaque application a une responsabilité précise.',
        styles['Body'],
    ))

    # 4.1 Structure
    story.append(Paragraph('4.1 Structure des Fichiers', styles['H2']))

    story.append(Paragraph(
        'e-learning 1.0/<br/>'
        '├── manage.py                  ← Point d\'entrée (commandes Django)<br/>'
        '├── requirements.txt           ← Liste des dépendances Python<br/>'
        '├── db.sqlite3                 ← Base de données<br/>'
        '├── env/                       ← Environnement virtuel Python<br/>'
        '├── elearning_backend/         ← Configuration principale<br/>'
        '│   ├── settings.py            ← Paramètres du projet<br/>'
        '│   ├── urls.py                ← Routage des URLs<br/>'
        '│   ├── wsgi.py                ← Serveur web<br/>'
        '│   └── asgi.py                ← Serveur asynchrone<br/>'
        '└── apps/                      ← Applications modulaires<br/>'
        '    ├── users/                 ← Modèle Utilisateur<br/>'
        '    ├── authentication/        ← Login, Register, Password<br/>'
        '    ├── courses/               ← Formations, Modules, Leçons<br/>'
        '    ├── enrollments/           ← Inscriptions et Paiements<br/>'
        '    ├── progress/              ← Suivi de progression<br/>'
        '    ├── quizzes/               ← Quiz, Questions, Réponses<br/>'
        '    ├── certificates/          ← Certificats PDF<br/>'
        '    └── dashboard/             ← Statistiques et Analytics',
        styles['CodeBlock'],
    ))

    # 4.2 Applications
    story.append(Paragraph('4.2 Les Applications Django', styles['H2']))

    story.append(Paragraph(
        'Dans Django, une <b>application</b> est un module autonome qui gère une partie du projet. '
        'Chaque application contient :',
        styles['Body'],
    ))

    app_structure = [
        '<b>models.py</b> : définit les données (tables de la base de données)',
        '<b>views.py</b> : la logique (traite les requêtes, retourne les réponses)',
        '<b>urls.py</b> : les adresses web (quel chemin → quelle vue)',
        '<b>serializers.py</b> : conversion Python ↔ JSON (spécifique aux APIs)',
        '<b>tests.py</b> : tests automatiques (vérifient que tout fonctionne)',
        '<b>admin.py</b> : configuration du panel d\'administration',
        '<b>services.py</b> : logique métier complexe (séparée des vues)',
        '<b>permissions.py</b> : règles d\'accès personnalisées',
        '<b>filters.py</b> : filtres pour la recherche et le tri',
    ]
    for item in app_structure:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    # 4.3 Modèle de données
    story.append(Paragraph('4.3 Modèle de Données (Relations)', styles['H2']))

    story.append(Paragraph(
        'Voici comment les données sont reliées entre elles :',
        styles['Body'],
    ))

    relations = [
        'Un <b>Utilisateur</b> a un <b>Profil</b> (OneToOne)',
        'Un <b>Formateur</b> (User) crée plusieurs <b>Formations</b> (OneToMany)',
        'Une <b>Formation</b> appartient à une <b>Catégorie</b> (ManyToOne)',
        'Une <b>Formation</b> contient plusieurs <b>Modules</b> (OneToMany)',
        'Un <b>Module</b> contient plusieurs <b>Leçons</b> (OneToMany)',
        'Un <b>Apprenant</b> (User) s\'inscrit à plusieurs <b>Formations</b> (ManyToMany via Enrollment)',
        'Un <b>Module</b> peut avoir un <b>Quiz</b> (OneToOne)',
        'Un <b>Quiz</b> contient plusieurs <b>Questions</b> (OneToMany)',
        'Une <b>Question</b> a plusieurs <b>Réponses</b> (OneToMany)',
        'Un <b>Apprenant</b> termine une Formation → obtient un <b>Certificat</b>',
    ]
    for item in relations:
        story.append(Paragraph(f'• {item}', styles['ListItem']))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # CHAPITRE 5 : GUIDE PAS À PAS
    # ═══════════════════════════════════════════════
    story.append(Paragraph('5. Guide pas à pas', styles['H1']))

    # 5.1 Installation
    story.append(Paragraph('5.1 Installer le Projet', styles['H2']))

    story.append(Paragraph(
        'Pour faire fonctionner le projet sur votre ordinateur :',
        styles['Body'],
    ))

    story.append(Paragraph(
        '# 1. Ouvrir un terminal dans le dossier du projet<br/>'
        'cd "e-learning 1.0"<br/><br/>'
        '# 2. Activer l\'environnement virtuel Python<br/>'
        '# L\'environnement virtuel isole les dépendances du projet<br/>'
        'source env/bin/activate<br/><br/>'
        '# 3. Installer les dépendances (si pas déjà fait)<br/>'
        'pip install -r requirements.txt<br/><br/>'
        '# 4. Appliquer les migrations (crée les tables en BDD)<br/>'
        'python manage.py migrate<br/><br/>'
        '# 5. Créer un superutilisateur (admin)<br/>'
        'python manage.py createsuperuser',
        styles['CodeBlock'],
    ))

    story.append(Paragraph(
        '<b>Qu\'est-ce qu\'un environnement virtuel ?</b><br/>'
        'C\'est une "bulle" isolée qui contient les bibliothèques Python du projet. '
        'Sans ça, les bibliothèques de différents projets se mélangeraient et pourraient entrer en conflit.',
        styles['NoteBlock'],
    ))

    # 5.2 Lancer le serveur
    story.append(Paragraph('5.2 Lancer le Serveur de Développement', styles['H2']))

    story.append(Paragraph(
        'Une fois le projet configuré, lancez le serveur :',
        styles['Body'],
    ))

    story.append(Paragraph(
        'python manage.py runserver',
        styles['CodeBlock'],
    ))

    story.append(Paragraph(
        'Le serveur démarre sur <b>http://127.0.0.1:8000/</b>. '
        'C\'est une adresse locale — uniquement accessible depuis votre ordinateur. '
        'Vous pouvez tester l\'API avec des outils comme <b>Postman</b>, <b>curl</b>, ou <b>l\'interface admin</b> '
        'sur <b>http://127.0.0.1:8000/admin/</b>.',
        styles['Body'],
    ))

    # 5.3 Tester les endpoints
    story.append(Paragraph('5.3 Tester les Endpoints avec curl', styles['H2']))

    story.append(Paragraph(
        '<b>Exemple 1 : Inscrire un nouvel utilisateur</b>',
        styles['BodyBold'],
    ))

    story.append(Paragraph(
        'curl -X POST http://127.0.0.1:8000/api/auth/register/ \\<br/>'
        '  -H "Content-Type: application/json" \\<br/>'
        '  -d \'{<br/>'
        '    "email": "jean@test.com",<br/>'
        '    "first_name": "Jean",<br/>'
        '    "last_name": "Dupont",<br/>'
        '    "password1": "MonMotDePasse123!",<br/>'
        '    "password2": "MonMotDePasse123!"<br/>'
        '  }\'',
        styles['CodeBlock'],
    ))

    story.append(Paragraph(
        '<b>Exemple 2 : Se connecter et obtenir un token</b>',
        styles['BodyBold'],
    ))

    story.append(Paragraph(
        'curl -X POST http://127.0.0.1:8000/api/auth/login/ \\<br/>'
        '  -H "Content-Type: application/json" \\<br/>'
        '  -d \'{<br/>'
        '    "email": "jean@test.com",<br/>'
        '    "password": "MonMotDePasse123!"<br/>'
        '  }\'',
        styles['CodeBlock'],
    ))

    story.append(Paragraph(
        '<b>Exemple 3 : Voir le catalogue des formations (public)</b>',
        styles['BodyBold'],
    ))

    story.append(Paragraph(
        'curl http://127.0.0.1:8000/api/courses/',
        styles['CodeBlock'],
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # CHAPITRE 6 : CONCEPTS CLÉS EXPLIQUÉS
    # ═══════════════════════════════════════════════
    story.append(Paragraph('6. Concepts Clés Expliqués', styles['H1']))

    # 6.1 Authentification JWT
    story.append(Paragraph('6.1 Authentification JWT en Détail', styles['H2']))

    story.append(Paragraph(
        'Le flux d\'authentification de notre projet fonctionne ainsi :',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>Étape 1 — Inscription</b> : L\'utilisateur crée un compte avec email + mot de passe.<br/>'
        '<b>Étape 2 — Connexion</b> : Il envoie son email + mot de passe au endpoint <b>/api/auth/login/</b>.<br/>'
        '<b>Étape 3 — Réception des tokens</b> : Le serveur retourne deux tokens :<br/>'
        '&nbsp;&nbsp;• <b>Access Token</b> (valide 30 minutes) — utilisé pour chaque requête<br/>'
        '&nbsp;&nbsp;• <b>Refresh Token</b> (valide 7 jours) — utilisé pour obtenir un nouveau Access Token<br/>'
        '<b>Étape 4 — Requête authentifiée</b> : L\'utilisateur inclut l\'Access Token dans chaque requête :<br/>'
        '&nbsp;&nbsp;<b>Authorization: Bearer &lt;token&gt;</b><br/>'
        '<b>Étape 5 — Rafraîchissement</b> : Quand l\'Access Token expire (après 30 min), '
        'on utilise le Refresh Token pour en obtenir un nouveau.<br/>'
        '<b>Étape 6 — Déconnexion</b> : Le Refresh Token est ajouté à la liste noire (blacklist).',
        styles['Body'],
    ))

    # 6.2 Sérialisation
    story.append(Paragraph('6.2 Sérialisation', styles['H2']))

    story.append(Paragraph(
        'Un <b>serializer</b> convertit les objets Python complexes (nos modèles de base de données) '
        'en format JSON (texte simple) que le frontend peut comprendre, et inversement.',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>Analogue :</b> Un serializer est comme un traducteur. '
        'Il traduit le "Python" en "JSON" (sérialisation) et le "JSON" en "Python" (désérialisation).',
        styles['NoteBlock'],
    ))

    story.append(Paragraph(
        'class FormationSerializer(serializers.ModelSerializer):<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;class Meta:<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;model = Formation<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Quels champs inclure dans le JSON<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;fields = [\'id\', \'titre\', \'prix\', \'niveau\']',
        styles['CodeBlock'],
    ))

    story.append(Paragraph(
        'Avant sérialisation (Python) :<br/>'
        '&nbsp;&nbsp;Formation(id=1, titre="Python", prix=5000, ...)<br/><br/>'
        'Après sérialisation (JSON) :<br/>'
        '&nbsp;&nbsp;{"id": 1, "titre": "Python", "prix": "5000.00", "niveau": "debutant"}',
        styles['Body'],
    ))

    # 6.3 Permissions
    story.append(Paragraph('6.3 Permissions', styles['H2']))

    story.append(Paragraph(
        'Les <b>permissions</b> contrôlent qui a le droit de faire quoi. '
        'Notre projet utilise plusieurs niveaux :',
        styles['Body'],
    ))

    perm_data = [
        ['AllowAny', 'Tout le monde (ex: catalogue public)'],
        ['IsAuthenticated', 'Utilisateurs connectés (ex: voir ses inscriptions)'],
        ['IsFormateurOrAdmin', 'Formateurs et admins (ex: créer une formation)'],
        ['IsAdministrateur', 'Admins uniquement (ex: gérer les catégories)'],
        ['IsFormateurOwnerOrAdmin', 'Propriétaire de la ressource ou admin (ex: modifier sa formation)'],
        ['IsPublishedOrOwnerOrAdmin', 'Formation publiée OU propriétaire OU admin (ex: voir une formation)'],
    ]

    perm_table = Table(
        [['Permission', 'Qui a accès']] + perm_data,
        colWidths=[5 * cm, 10.5 * cm],
    )
    perm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(perm_table)

    # 6.4 Migrations
    story.append(Paragraph('6.4 Migrations', styles['H2']))

    story.append(Paragraph(
        'Une <b>migration</b> est un fichier qui décrit comment modifier la base de données '
        'quand on change les modèles. C\'est le système de "versionnage" de la base de données.',
        styles['Body'],
    ))

    story.append(Paragraph(
        '<b>Analogue :</b> Si votre base de données est un bâtiment, une migration est un plan '
        'de rénovation. Elle dit "ajoute une pièce", "agrandis la cuisine", etc.',
        styles['NoteBlock'],
    ))

    story.append(Paragraph(
        '# 1. Après avoir modifié un modèle, générer la migration<br/>'
        'python manage.py makemigrations<br/><br/>'
        '# 2. Appliquer la migration à la base de données<br/>'
        'python manage.py migrate',
        styles['CodeBlock'],
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    # CHAPITRE 7 : LEXIQUE
    # ═══════════════════════════════════════════════
    story.append(Paragraph('7. Lexique pour Débutants', styles['H1']))

    story.append(Paragraph(
        'Voici les termes techniques utilisés dans ce projet, expliqués simplement :',
        styles['Body'],
    ))

    lexique = [
        ['API', 'Interface qui permet à deux programmes de communiquer'],
        ['Backend', 'Partie invisible du logiciel (serveur, base de données)'],
        ['Frontend', 'Partie visible (interface utilisateur dans le navigateur)'],
        ['Endpoint', 'Adresse URL d\'une fonctionnalité de l\'API'],
        ['JSON', 'Format de texte structuré pour échanger des données'],
        ['HTTP', 'Protocole de communication sur Internet'],
        ['Requête (Request)', 'Message envoyé du client vers le serveur'],
        ['Réponse (Response)', 'Message retourné par le serveur au client'],
        ['JWT', 'Jeton d\'authentification (comme un badge d\'accès)'],
        ['Token', 'Jeton — preuve numérique d\'identité'],
        ['ORM', 'Outil qui traduit le Python en requêtes base de données'],
        ['Modèle (Model)', 'Classe Python qui représente une table en base de données'],
        ['Migration', 'Fichier qui décrit les changements de la base de données'],
        ['Serializer', 'Convertisseur Python ↔ JSON'],
        ['Permission', 'Règle qui dit "qui a le droit de faire quoi"'],
        ['CRUD', 'Create, Read, Update, Delete — les 4 opérations de base'],
        ['UUID', 'Identifiant unique généré automatiquement (ex: a1b2c3d4-...)'],
        ['ForeignKey', 'Lien entre deux tables (ex: une formation appartient à un formateur)'],
        ['Webhook', 'Notification automatique envoyée par un service externe'],
        ['Environnement virtuel', '"Bulle" isolée pour les dépendances d\'un projet'],
    ]

    lexique_table = Table(
        [['Terme', 'Définition']] + lexique,
        colWidths=[4.5 * cm, 11 * cm],
    )
    lexique_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(lexique_table)

    story.append(Spacer(1, 10 * mm))

    # ── Pied de page final ──────────────────────────────────────
    story.append(HRFlowable(
        width="100%", thickness=1, color=BORDER,
        spaceBefore=10, spaceAfter=10,
    ))
    story.append(Paragraph(
        '<i>Document généré automatiquement le ' + datetime.now().strftime('%d %B %Y') +
        ' — Plateforme E-Learning v1.0 — EFG Platform</i>',
        ParagraphStyle(
            'Footer', parent=styles['Normal'],
            fontName='Helvetica-Oblique', fontSize=8, leading=12,
            textColor=LIGHT_TEXT, alignment=TA_CENTER,
        ),
    ))

    # ── Génération ──────────────────────────────────────────────
    doc.build(story)
    print(f"✅ Document généré : {output_path}")
    return output_path


if __name__ == '__main__':
    build_document()
