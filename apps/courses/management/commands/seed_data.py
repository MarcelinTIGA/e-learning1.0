"""
Commande de seeding : python manage.py seed_data

Crée un jeu de données de test complet pour tester tous les flux Flutter :
  - 3 catégories
  - 1 formateur (seed_formateur@efg.com / Formateur123!)
  - 1 apprenant (seed_apprenant@efg.com / Apprenant123!)
  - 2 formations publiées avec modules, leçons, quiz complets
  - 1 formation non publiée (brouillon)
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Crée des données de test pour l'app e-learning"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprime toutes les données existantes avant de seeder',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.users.models import User
        from apps.courses.models import Category, Formation, Module, Lesson
        from apps.quizzes.models import Quiz, Question, Answer

        if options['reset']:
            self.stdout.write('Suppression des données existantes...')
            Answer.objects.all().delete()
            Question.objects.all().delete()
            Quiz.objects.all().delete()
            Lesson.objects.all().delete()
            Module.objects.all().delete()
            Formation.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(email__endswith='@efg.com').delete()
            self.stdout.write(self.style.WARNING('Données supprimées.'))

        # ── Catégories ──────────────────────────────────────────────────
        cat_dev, _ = Category.objects.get_or_create(
            slug='developpement-web',
            defaults={'name': 'Développement Web', 'description': 'HTML, CSS, JavaScript, frameworks modernes'}
        )
        cat_mobile, _ = Category.objects.get_or_create(
            slug='developpement-mobile',
            defaults={'name': 'Développement Mobile', 'description': 'Flutter, React Native, Android, iOS'}
        )
        cat_data, _ = Category.objects.get_or_create(
            slug='data-science',
            defaults={'name': 'Data Science', 'description': 'Python, Machine Learning, analyses de données'}
        )
        self.stdout.write(f'  Catégories : {Category.objects.count()}')

        # ── Utilisateurs ─────────────────────────────────────────────────
        formateur, created = User.objects.get_or_create(
            email='seed_formateur@efg.com',
            defaults={
                'first_name': 'Jean',
                'last_name': 'Formateur',
                'role': User.Role.FORMATEUR,
                'is_active': True,
            }
        )
        if created:
            formateur.set_password('Formateur123!')
            formateur.save()
        self.stdout.write(f'  Formateur : {formateur.email} ({"créé" if created else "existant"})')

        apprenant, created = User.objects.get_or_create(
            email='seed_apprenant@efg.com',
            defaults={
                'first_name': 'Marie',
                'last_name': 'Apprenante',
                'role': User.Role.APPRENANT,
                'is_active': True,
            }
        )
        if created:
            apprenant.set_password('Apprenant123!')
            apprenant.save()
        self.stdout.write(f'  Apprenant : {apprenant.email} ({"créé" if created else "existant"})')

        # ── Formation 1 : Python pour débutants (payante) ─────────────────
        f1, _ = Formation.objects.get_or_create(
            titre='Python pour Débutants',
            formateur=formateur,
            defaults={
                'description': (
                    'Apprenez Python de zéro ! Ce cours couvre les bases du langage, '
                    'la programmation orientée objet, et des projets pratiques. '
                    'Idéal pour toute personne souhaitant se lancer dans la programmation.'
                ),
                'prix': 15000,
                'niveau': 'debutant',
                'categorie': cat_dev,
                'is_published': True,
            }
        )

        # Module 1 : Introduction
        m1, _ = Module.objects.get_or_create(
            formation=f1, order=1,
            defaults={'titre': 'Introduction à Python', 'description': 'Découverte du langage Python et configuration de l\'environnement'}
        )
        Lesson.objects.get_or_create(
            module=m1, order=1,
            defaults={
                'titre': 'Qu\'est-ce que Python ?',
                'content_type': 'video',
                'video_url': 'https://www.youtube.com/watch?v=rfscVS0vtbw',
                'duration_minutes': 10,
                'is_preview': True,
            }
        )
        Lesson.objects.get_or_create(
            module=m1, order=2,
            defaults={
                'titre': 'Installation et premier programme',
                'content_type': 'text',
                'text_content': (
                    '## Installation de Python\n\n'
                    '1. Téléchargez Python sur python.org\n'
                    '2. Cochez "Add to PATH" lors de l\'installation\n'
                    '3. Ouvrez un terminal et tapez `python --version`\n\n'
                    '## Votre premier programme\n\n'
                    '```python\nprint("Bonjour le monde!")\n```\n\n'
                    'Ce programme affiche "Bonjour le monde!" dans le terminal.'
                ),
                'duration_minutes': 15,
                'is_preview': True,
            }
        )
        Lesson.objects.get_or_create(
            module=m1, order=3,
            defaults={
                'titre': 'Variables et types de données',
                'content_type': 'text',
                'text_content': (
                    '## Les variables en Python\n\n'
                    'En Python, une variable est créée en lui assignant une valeur :\n\n'
                    '```python\nnom = "Alice"\nage = 25\ntaille = 1.70\nest_etudiant = True\n```\n\n'
                    '## Types principaux\n\n'
                    '- `str` : chaînes de caractères\n'
                    '- `int` : nombres entiers\n'
                    '- `float` : nombres décimaux\n'
                    '- `bool` : True ou False\n'
                ),
                'duration_minutes': 20,
                'is_preview': False,
            }
        )

        # Quiz module 1
        quiz1, _ = Quiz.objects.get_or_create(
            module=m1,
            defaults={'titre': 'Quiz : Introduction à Python', 'passing_score': 70}
        )
        self._add_questions(quiz1, [
            {
                'text': 'Quel symbole utilise-t-on pour un commentaire en Python ?',
                'type': 'qcm',
                'answers': [
                    ('// comme en Java', False),
                    ('# le dièse', True),
                    ('/* ... */', False),
                    ('-- double tiret', False),
                ]
            },
            {
                'text': 'Python est un langage interprété.',
                'type': 'vrai_faux',
                'answers': [
                    ('Vrai', True),
                    ('Faux', False),
                ]
            },
            {
                'text': 'Quelle fonction affiche du texte dans le terminal en Python ?',
                'type': 'qcm',
                'answers': [
                    ('console.log()', False),
                    ('echo()', False),
                    ('print()', True),
                    ('write()', False),
                ]
            },
        ])

        # Module 2 : Structures de contrôle
        m2, _ = Module.objects.get_or_create(
            formation=f1, order=2,
            defaults={'titre': 'Structures de contrôle', 'description': 'Conditions, boucles et fonctions'}
        )
        Lesson.objects.get_or_create(
            module=m2, order=1,
            defaults={
                'titre': 'Les conditions : if, elif, else',
                'content_type': 'text',
                'text_content': (
                    '## Les conditions en Python\n\n'
                    '```python\nage = 18\n\nif age >= 18:\n    print("Majeur")\nelif age >= 15:\n    print("Adolescent")\nelse:\n    print("Enfant")\n```\n\n'
                    'Python utilise l\'indentation (4 espaces) pour délimiter les blocs.'
                ),
                'duration_minutes': 25,
                'is_preview': False,
            }
        )
        Lesson.objects.get_or_create(
            module=m2, order=2,
            defaults={
                'titre': 'Les boucles : for et while',
                'content_type': 'video',
                'video_url': 'https://www.youtube.com/watch?v=94UHCEmprCY',
                'duration_minutes': 30,
                'is_preview': False,
            }
        )

        quiz2, _ = Quiz.objects.get_or_create(
            module=m2,
            defaults={'titre': 'Quiz : Structures de contrôle', 'passing_score': 70}
        )
        self._add_questions(quiz2, [
            {
                'text': 'Quelle est la bonne syntaxe d\'une condition en Python ?',
                'type': 'qcm',
                'answers': [
                    ('if (x > 0) { }', False),
                    ('if x > 0:', True),
                    ('if x > 0 then', False),
                    ('when x > 0:', False),
                ]
            },
            {
                'text': 'La boucle `for` en Python ne peut itérer que sur des listes.',
                'type': 'vrai_faux',
                'answers': [
                    ('Vrai', False),
                    ('Faux', True),
                ]
            },
            {
                'text': 'Quel mot-clé arrête immédiatement une boucle en Python ?',
                'type': 'qcm',
                'answers': [
                    ('stop', False),
                    ('exit', False),
                    ('break', True),
                    ('end', False),
                ]
            },
        ])

        self.stdout.write(f'  Formation 1 : "{f1.titre}" — {f1.modules.count()} modules')

        # ── Formation 2 : Flutter & Dart (payante) ────────────────────────
        f2, _ = Formation.objects.get_or_create(
            titre='Flutter & Dart : Application Mobile Complète',
            formateur=formateur,
            defaults={
                'description': (
                    'Créez des applications mobiles multiplateformes avec Flutter et Dart. '
                    'De l\'installation à la publication sur les stores, ce cours couvre tout '
                    'ce dont vous avez besoin pour devenir développeur mobile.'
                ),
                'prix': 25000,
                'niveau': 'intermediaire',
                'categorie': cat_mobile,
                'is_published': True,
            }
        )

        m3, _ = Module.objects.get_or_create(
            formation=f2, order=1,
            defaults={'titre': 'Bases de Dart', 'description': 'Le langage Dart avant Flutter'}
        )
        Lesson.objects.get_or_create(
            module=m3, order=1,
            defaults={
                'titre': 'Introduction à Dart',
                'content_type': 'video',
                'video_url': 'https://www.youtube.com/watch?v=5xlVP04905w',
                'duration_minutes': 20,
                'is_preview': True,
            }
        )
        Lesson.objects.get_or_create(
            module=m3, order=2,
            defaults={
                'titre': 'Variables, types et null safety',
                'content_type': 'text',
                'text_content': (
                    '## Null Safety en Dart\n\n'
                    'Dart 2.12+ introduit le null safety :\n\n'
                    '```dart\nString nom = "Alice";  // non-nullable\nString? prenom;       // nullable\n\nint longueur = nom.length;  // OK\nint? len = prenom?.length;  // null si prenom est null\n```\n\n'
                    'Utilisez `!` pour affirmer qu\'une valeur n\'est pas null (risqué !).'
                ),
                'duration_minutes': 25,
                'is_preview': False,
            }
        )

        quiz3, _ = Quiz.objects.get_or_create(
            module=m3,
            defaults={'titre': 'Quiz : Bases de Dart', 'passing_score': 70}
        )
        self._add_questions(quiz3, [
            {
                'text': 'Quel opérateur Dart permet d\'accéder à une propriété seulement si l\'objet n\'est pas null ?',
                'type': 'qcm',
                'answers': [
                    ('.', False),
                    ('?.', True),
                    ('!.', False),
                    ('??', False),
                ]
            },
            {
                'text': 'En Dart, `var` est typé statiquement à la compilation.',
                'type': 'vrai_faux',
                'answers': [
                    ('Vrai', True),
                    ('Faux', False),
                ]
            },
        ])

        self.stdout.write(f'  Formation 2 : "{f2.titre}" — {f2.modules.count()} modules')

        # ── Formation 3 : Brouillon (non publiée) ─────────────────────────
        f3, _ = Formation.objects.get_or_create(
            titre='Machine Learning avec Python (En cours de rédaction)',
            formateur=formateur,
            defaults={
                'description': 'Introduction au Machine Learning avec scikit-learn et pandas.',
                'prix': 30000,
                'niveau': 'avance',
                'categorie': cat_data,
                'is_published': False,
            }
        )
        self.stdout.write(f'  Formation 3 (brouillon) : "{f3.titre}"')

        # ── Résumé ────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Seeding terminé !'))
        self.stdout.write('')
        self.stdout.write('Comptes de test :')
        self.stdout.write(f'  Formateur  : seed_formateur@efg.com / Formateur123!')
        self.stdout.write(f'  Apprenant  : seed_apprenant@efg.com / Apprenant123!')
        self.stdout.write('')
        self.stdout.write('Données créées :')
        self.stdout.write(f'  Catégories : {Category.objects.count()}')
        self.stdout.write(f'  Formations : {Formation.objects.count()} ({Formation.objects.filter(is_published=True).count()} publiées)')
        self.stdout.write(f'  Modules    : {Module.objects.count()}')
        self.stdout.write(f'  Leçons     : {Lesson.objects.count()}')
        self.stdout.write(f'  Quiz       : {Quiz.objects.count()}')
        from apps.quizzes.models import Question
        self.stdout.write(f'  Questions  : {Question.objects.count()}')

    def _add_questions(self, quiz, questions_data):
        from apps.quizzes.models import Question, Answer
        for i, q_data in enumerate(questions_data, start=1):
            question, created = Question.objects.get_or_create(
                quiz=quiz,
                order=i,
                defaults={
                    'text': q_data['text'],
                    'question_type': q_data['type'],
                    'points': 1,
                }
            )
            if created:
                for answer_text, is_correct in q_data['answers']:
                    Answer.objects.create(
                        question=question,
                        text=answer_text,
                        is_correct=is_correct,
                    )
