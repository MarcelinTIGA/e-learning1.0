"""
Services pour l'app 'dashboard'.

Contient la logique d'agrégation des statistiques pour chaque rôle.

AMBIGUÏTÉ : Pourquoi un service plutôt que de calculer dans la view ?
  - Les calculs sont complexes (requêtes SQL agrégées, compteurs)
  - Ils pourraient être réutilisés ailleurs (API externe, rapport CSV)
  - Séparer la logique métier de la couche HTTP (bonnes pratiques DRF)

AMBIGUÏTÉ : Pourquoi pas des vues SQL / Materialized Views ?
  - SQLite ne supporte pas les vues matérialisées
  - En production avec PostgreSQL, on pourrait optimiser ainsi
  - Pour l'instant, les requêtes Django ORM sont suffisantes
"""

from decimal import Decimal

from django.db.models import Count, Q, Sum

from apps.courses.models import Formation
from apps.enrollments.models import Enrollment
from apps.users.models import User


class DashboardService:
    """Agrégation de statistiques pour les dashboards."""

    # ─────────────────────────────────────────────
    # STUDENT
    # ─────────────────────────────────────────────

    @staticmethod
    def get_student_dashboard(user):
        """
        Retourne les données du dashboard pour un apprenant.

        Args:
            user: l'apprenant connecté

        Returns:
            dict: données du dashboard
        """
        from apps.enrollments.models import Enrollment
        from apps.progress.models import FormationProgress

        # Inscriptions
        enrollments = Enrollment.objects.filter(user=user)
        total = enrollments.count()
        active = enrollments.filter(status=Enrollment.Status.ACTIVE).count()
        completed = enrollments.filter(status=Enrollment.Status.COMPLETED).count()

        # Certificats
        certificates_count = user.certificates.count()

        # Formations en cours avec progression
        # AMBIGUÏTÉ : Pourquoi select_related + prefetch_related ici ?
        #   - select_related('formation') : charge la formation en 1 requête (JOIN)
        #   - Sans ça, chaque formation serait chargée individuellement (N+1 queries)
        current_progress = []
        for enrollment in enrollments.filter(status=Enrollment.Status.ACTIVE).select_related('formation'):
            try:
                progress = FormationProgress.objects.get(
                    user=user, formation=enrollment.formation
                )
                current_progress.append({
                    'formation_id': enrollment.formation.pk,
                    'formation_titre': enrollment.formation.titre,
                    'percentage': float(progress.percentage),
                    'is_completed': progress.is_completed,
                    'last_accessed_lesson': (
                        progress.last_accessed_lesson.titre
                        if progress.last_accessed_lesson else None
                    ),
                })
            except FormationProgress.DoesNotExist:
                pass

        # Dernière activité (5 dernières leçons accédées)
        recent_activity = []
        progresses = FormationProgress.objects.filter(
            user=user,
            last_accessed_lesson__isnull=False,
        ).select_related('last_accessed_lesson', 'formation').order_by('-last_accessed_at')[:5]

        for progress in progresses:
            recent_activity.append({
                'formation_titre': progress.formation.titre,
                'lesson_titre': progress.last_accessed_lesson.titre,
                'accessed_at': progress.last_accessed_at,
            })

        return {
            'total_enrollments': total,
            'active_enrollments': active,
            'completed_enrollments': completed,
            'certificates_count': certificates_count,
            'current_progress': current_progress,
            'recent_activity': recent_activity,
        }

    # ─────────────────────────────────────────────
    # FORMATEUR
    # ─────────────────────────────────────────────

    @staticmethod
    def get_formateur_dashboard(user):
        """
        Retourne les données du dashboard pour un formateur.

        Args:
            user: le formateur connecté

        Returns:
            dict: données du dashboard
        """
        formations = Formation.objects.filter(formateur=user)

        total_formations = formations.count()
        published_formations = formations.filter(is_published=True).count()

        # Statistiques par formation
        formations_stats = []
        total_students_set = set()  # Pour compter les étudiants uniques
        total_revenue = Decimal('0.00')

        for formation in formations.select_related('categorie').prefetch_related('enrollments'):
            enrollments_count = formation.enrollments.filter(
                status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED]
            ).count()

            # Ajouter les étudiants au set unique
            for enrollment in formation.enrollments.filter(
                status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED]
            ).select_related('user'):
                total_students_set.add(enrollment.user.pk)

            # Revenu : seulement les formations payantes avec inscription active/complétée
            revenue = formation.enrollments.filter(
                status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED]
            ).aggregate(total=Sum('formation__prix'))['total'] or 0

            total_revenue += Decimal(str(revenue))

            formations_stats.append({
                'formation_id': formation.pk,
                'titre': formation.titre,
                'is_published': formation.is_published,
                'students_count': enrollments_count,
                'revenue': float(revenue),
            })

        # Dernières inscriptions
        recent_enrollments = []
        for enrollment in Enrollment.objects.filter(
            formation__formateur=user,
        ).select_related('user', 'formation').order_by('-enrolled_at')[:10]:
            recent_enrollments.append({
                'user_name': enrollment.user.full_name,
                'user_email': enrollment.user.email,
                'formation_titre': enrollment.formation.titre,
                'status': enrollment.status,
                'enrolled_at': enrollment.enrolled_at,
            })

        return {
            'total_formations': total_formations,
            'published_formations': published_formations,
            'total_students': len(total_students_set),
            'total_revenue': total_revenue,
            'formations_stats': formations_stats,
            'recent_enrollments': recent_enrollments,
        }

    # ─────────────────────────────────────────────
    # ADMIN
    # ─────────────────────────────────────────────

    @staticmethod
    def get_admin_dashboard():
        """
        Retourne les données du dashboard pour un administrateur.

        Returns:
            dict: données du dashboard
        """
        # Utilisateurs
        total_users = User.objects.count()
        total_apprenants = User.objects.filter(role=User.Role.APPRENANT).count()
        total_formateurs = User.objects.filter(role=User.Role.FORMATEUR).count()

        # Formations
        total_formations = Formation.objects.count()
        published_formations = Formation.objects.filter(is_published=True).count()

        # Inscriptions
        total_enrollments = Enrollment.objects.count()

        # Revenu total
        # AMBIGUÏTÉ : Comment calculer le revenu total ?
        #   - Option 1 : Somme des prix des formations × nb d'inscriptions
        #     → Ne tient pas compte des formations gratuites
        #   - Option 2 : Somme des montants des Payments réussis
        #     → Plus précis mais nécessite les données Payment
        #   - On utilise Option 1 (plus simple, cohérent avec le formateur dashboard)
        total_revenue = Decimal('0.00')
        for enrollment in Enrollment.objects.filter(
            status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED]
        ).select_related('formation'):
            if not enrollment.formation.is_free:
                total_revenue += enrollment.formation.prix

        # Certificats
        from apps.certificates.models import Certificate
        certificates_issued = Certificate.objects.count()

        # Derniers utilisateurs
        recent_users = []
        for user in User.objects.order_by('-date_joined')[:10]:
            recent_users.append({
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'date_joined': user.date_joined,
            })

        # Activité récente (dernières inscriptions + dernières terminaisons)
        recent_activity = []

        # Dernières inscriptions
        for enrollment in Enrollment.objects.select_related(
            'user', 'formation'
        ).order_by('-enrolled_at')[:5]:
            recent_activity.append({
                'type': 'inscription',
                'user': enrollment.user.full_name,
                'formation': enrollment.formation.titre,
                'date': enrollment.enrolled_at,
            })

        # Dernières terminaisons (via FormationProgress)
        from apps.progress.models import FormationProgress
        for progress in FormationProgress.objects.filter(
            is_completed=True,
        ).select_related('user', 'formation').order_by('-last_accessed_at')[:5]:
            recent_activity.append({
                'type': 'completion',
                'user': progress.user.full_name,
                'formation': progress.formation.titre,
                'date': progress.last_accessed_at,
            })

        # Trier par date décroissante
        recent_activity.sort(key=lambda x: x['date'], reverse=True)

        return {
            'total_users': total_users,
            'total_apprenants': total_apprenants,
            'total_formateurs': total_formateurs,
            'total_formations': total_formations,
            'published_formations': published_formations,
            'total_enrollments': total_enrollments,
            'total_revenue': total_revenue,
            'certificates_issued': certificates_issued,
            'recent_users': recent_users,
            'recent_activity': recent_activity[:10],  # Top 10
        }
