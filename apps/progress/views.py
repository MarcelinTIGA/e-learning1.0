"""
Views pour l'app 'progress'.

Endpoints disponibles :
    GET  /api/progress/formations/                    — Mes progressions par formation
    GET  /api/progress/formations/<formation_id>/     — Progression dans une formation
    GET  /api/progress/formations/<formation_id>/resume/  — Reprendre où j'en étais
    POST /api/progress/lessons/<lesson_id>/complete/  — Marquer une leçon comme terminée
    POST /api/progress/lessons/<lesson_id>/video/     — Sauvegarder position vidéo
    GET  /api/progress/lessons/<lesson_id>/           — État d'une leçon
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FormationProgress, LessonProgress
from .serializers import (
    FormationProgressSerializer,
    LessonProgressSerializer,
    VideoPositionSerializer,
)
from .services import ProgressService


class FormationProgressListView(generics.ListAPIView):
    """
    GET /api/progress/formations/
    Retourne la progression de l'apprenant dans toutes ses formations.
    Permet d'afficher le tableau de bord "mes cours en cours".
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FormationProgressSerializer

    def get_queryset(self):
        """
        Retourne uniquement les progressions de l'utilisateur connecté.
        select_related : charge formation et last_accessed_lesson en une seule requête.
        """
        return FormationProgress.objects.filter(
            user=self.request.user
        ).select_related('formation', 'last_accessed_lesson')


class FormationProgressDetailView(generics.RetrieveAPIView):
    """
    GET /api/progress/formations/<formation_id>/
    Progression détaillée dans une formation spécifique.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FormationProgressSerializer

    def get_object(self):
        """
        Récupère ou crée la progression pour cette formation.
        Si l'apprenant accède pour la première fois, un enregistrement vide est créé.
        """
        formation_id = self.kwargs.get('formation_id')
        # get_or_create : retourne la progression existante ou en crée une nouvelle (vide)
        progress, _ = FormationProgress.objects.get_or_create(
            user=self.request.user,
            formation_id=formation_id,
        )
        return progress


class ResumeFormationView(APIView):
    """
    GET /api/progress/formations/<formation_id>/resume/
    Retourne la dernière leçon accédée pour reprendre la formation.

    Utilisé par le frontend pour le bouton "Continuer" sur la page de la formation.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, formation_id):
        try:
            progress = FormationProgress.objects.select_related(
                'last_accessed_lesson'
            ).get(user=request.user, formation_id=formation_id)
        except FormationProgress.DoesNotExist:
            # L'apprenant n'a pas encore commencé cette formation
            return Response(
                {'detail': "Vous n'avez pas encore commencé cette formation.", 'lesson_id': None},
                status=status.HTTP_200_OK,
            )

        if not progress.last_accessed_lesson:
            return Response(
                {'detail': "Vous n'avez pas encore accédé à une leçon.", 'lesson_id': None},
                status=status.HTTP_200_OK,
            )

        # Retourner l'ID et le titre de la leçon pour que le frontend puisse rediriger
        return Response({
            'lesson_id':    progress.last_accessed_lesson.pk,
            'lesson_titre': progress.last_accessed_lesson.titre,
        })


class MarkLessonCompleteView(APIView):
    """
    POST /api/progress/lessons/<lesson_id>/complete/
    Marque une leçon comme terminée et recalcule la progression.

    Aucun corps JSON requis (simple POST suffit).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lesson_id):
        try:
            lesson_progress = ProgressService.mark_lesson_complete(
                user=request.user,
                lesson_id=lesson_id,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LessonProgressSerializer(lesson_progress).data)


class SaveVideoPositionView(APIView):
    """
    POST /api/progress/lessons/<lesson_id>/video/
    Sauvegarde la position actuelle dans une vidéo.

    Corps JSON attendu :
        { "position_seconds": 245 }

    Appelé automatiquement par le lecteur vidéo du frontend.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lesson_id):
        # Valider les données entrantes
        serializer = VideoPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lesson_progress = ProgressService.save_video_position(
                user=request.user,
                lesson_id=lesson_id,
                position_seconds=serializer.validated_data['position_seconds'],
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LessonProgressSerializer(lesson_progress).data)


class LessonProgressDetailView(APIView):
    """
    GET /api/progress/lessons/<lesson_id>/
    Retourne l'état d'avancement pour une leçon spécifique.

    Utilisé par le frontend pour :
        - Afficher si la leçon est terminée (coche verte ou non)
        - Reprendre la vidéo à la bonne position
        - Mettre à jour last_accessed_at (tracking)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lesson_id):
        # Obtenir ou créer le suivi (marque automatiquement l'accès)
        from apps.courses.models import Lesson as LessonModel
        try:
            lesson = LessonModel.objects.select_related('module__formation').get(pk=lesson_id)
        except LessonModel.DoesNotExist:
            return Response({'detail': "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)

        lesson_progress = ProgressService.get_or_create_lesson_progress(
            user=request.user,
            lesson=lesson,
        )

        # Mettre à jour la "dernière leçon accédée" dans FormationProgress
        try:
            ProgressService.update_last_accessed(
                user=request.user,
                lesson_id=lesson_id,
            )
        except Exception:
            # Non bloquant : si ça échoue, on retourne quand même la progression
            pass

        return Response(LessonProgressSerializer(lesson_progress).data)
