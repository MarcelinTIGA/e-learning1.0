"""
Services métier pour l'app 'quizzes'.

Un "service" regroupe la logique métier complexe dans une classe séparée,
pour ne pas surcharger les views ou les modèles.

Services disponibles :
    - QuizGradingService.grade_submission() : corrige une soumission de quiz
    - can_access_module()                   : vérifie si un module est débloqué
"""

from decimal import Decimal  # Pour les calculs précis de pourcentage

from django.db import transaction  # Pour les transactions atomiques (tout ou rien)

from .models import Answer, AttemptAnswer, Quiz, QuizAttempt


class QuizGradingService:
    """
    Service de correction automatique des quiz.

    Responsabilités :
        1. Valider les réponses soumises
        2. Calculer le score en pourcentage
        3. Créer l'enregistrement QuizAttempt en base de données
        4. Créer les AttemptAnswer pour chaque réponse donnée
    """

    @staticmethod
    @transaction.atomic
    def grade_submission(user, quiz_id, answers_data):
        """
        Corrige une soumission de quiz et retourne la tentative créée.

        Args:
            user        : l'utilisateur qui soumet le quiz (instance User)
            quiz_id     : ID du quiz à corriger
            answers_data: liste de dict [{'question_id': 1, 'answer_id': 3}, ...]

        Returns:
            QuizAttempt : l'objet tentative créé avec le score calculé

        Raises:
            Quiz.DoesNotExist : si le quiz n'existe pas
            ValueError        : si les données sont invalides

        Fonctionnement de @transaction.atomic :
            Si une erreur survient au milieu de la correction, TOUTES les
            modifications en base sont annulées (pas de données partielles).
        """
        # Récupère le quiz avec toutes ses questions et réponses en une seule requête
        # prefetch_related : charge questions → answers d'un coup (évite N requêtes SQL)
        quiz = Quiz.objects.prefetch_related('questions__answers').get(pk=quiz_id)

        # Construire un dictionnaire {question_id: answer_id} depuis les données soumises
        # Facilite la recherche en O(1) plutôt que parcourir la liste à chaque fois
        submitted = {item['question_id']: item.get('answer_id') for item in answers_data}

        earned_points = 0   # Points gagnés par l'apprenant
        total_points = 0    # Total des points possibles

        # Prépare les données pour créer les AttemptAnswer en lot (bulk_create = plus rapide)
        attempt_answers_to_create = []

        for question in quiz.questions.all():
            total_points += question.points  # Additionne les points de chaque question

            # Récupère la réponse sélectionnée par l'apprenant pour cette question
            answer_id = submitted.get(question.id)
            selected_answer = None
            is_correct = False

            if answer_id:
                try:
                    # Vérifie que la réponse appartient bien à cette question (sécurité)
                    selected_answer = question.answers.get(pk=answer_id)
                    is_correct = selected_answer.is_correct

                    if is_correct:
                        earned_points += question.points  # Ajoute les points si correct
                except Answer.DoesNotExist:
                    # Si l'answer_id ne correspond à aucune réponse de cette question
                    pass

            # Prépare l'AttemptAnswer (sera sauvegardé en lot après)
            attempt_answers_to_create.append(
                AttemptAnswer(
                    question=question,
                    selected_answer=selected_answer,
                    is_correct=is_correct,
                )
            )

        # Calcul du score en pourcentage
        # Decimal pour éviter les erreurs d'arrondi des float (ex: 0.1 + 0.2 ≠ 0.3 en float)
        if total_points > 0:
            score = Decimal(earned_points) / Decimal(total_points) * 100
            score = round(score, 2)  # Arrondi à 2 décimales
        else:
            score = Decimal('0.00')

        # Détermine si le quiz est validé (score >= seuil de validation)
        passed = score >= Decimal(quiz.passing_score)

        # Crée l'objet QuizAttempt en base de données
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz,
            score=score,
            earned_points=earned_points,
            total_points=total_points,
            passed=passed,
        )

        # Assigne la tentative à chaque AttemptAnswer et les crée en lot
        # bulk_create : insère tous les objets en une seule requête SQL (beaucoup plus rapide)
        for attempt_answer in attempt_answers_to_create:
            attempt_answer.attempt = attempt
        AttemptAnswer.objects.bulk_create(attempt_answers_to_create)

        return attempt


def can_access_module(user, module):
    """
    Vérifie si un apprenant peut accéder à un module donné.

    Règle de déblocage progressif :
        - Le premier module (order=1) est toujours accessible.
        - Les modules suivants sont accessibles seulement si le module précédent est complété :
            * Toutes les leçons du module précédent ont été vues (LessonProgress.completed=True)
            * Le quiz du module précédent a été validé (QuizAttempt.passed=True)
              (uniquement si ce module a un quiz)

    Args:
        user   : l'utilisateur à vérifier (instance User)
        module : le module auquel on veut accéder (instance Module)

    Returns:
        bool : True si l'accès est autorisé, False sinon
    """
    # Le premier module est toujours libre d'accès
    if module.order == 1:
        return True

    # Cherche le module précédent dans la même formation
    try:
        previous_module = module.formation.modules.get(order=module.order - 1)
    except module.__class__.DoesNotExist:
        # Pas de module précédent trouvé → accès autorisé par défaut
        return True

    # Vérifie que toutes les leçons du module précédent ont été complétées
    # Import ici pour éviter les imports circulaires (quizzes ↔ progress)
    try:
        from apps.progress.models import LessonProgress

        total_lessons = previous_module.lessons.count()

        if total_lessons > 0:
            # Compte les leçons complétées par cet utilisateur dans le module précédent
            completed_lessons = LessonProgress.objects.filter(
                user=user,
                lesson__module=previous_module,
                completed=True,
            ).count()

            # Toutes les leçons doivent être complétées
            if completed_lessons < total_lessons:
                return False

    except ImportError:
        # Si l'app progress n'existe pas encore, on ignore cette vérification
        pass

    # Vérifie que le quiz du module précédent a été validé (s'il en a un)
    if hasattr(previous_module, 'quiz'):
        try:
            quiz = previous_module.quiz
            # Cherche une tentative réussie de cet utilisateur pour ce quiz
            has_passed = QuizAttempt.objects.filter(
                user=user,
                quiz=quiz,
                passed=True,
            ).exists()

            if not has_passed:
                return False  # Quiz non validé → module suivant bloqué

        except Quiz.DoesNotExist:
            # Le module précédent n'a pas de quiz → pas de blocage
            pass

    return True  # Toutes les conditions remplies → accès autorisé
