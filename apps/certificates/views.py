"""
Views pour l'app 'certificates'.

Endpoints disponibles :
    GET    /api/certificates/                         — Mes certificats (apprenant) / tous (admin)
    POST   /api/certificates/                         — Créer un certificat (admin)
    GET    /api/certificates/<id>/                    — Détail d'un certificat
    GET    /api/certificates/<id>/download/           — Télécharger le PDF
    POST   /api/certificates/verify/<code>/           — Vérifier un certificat
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Certificate
from .serializers import (
    CertificateCreateSerializer,
    CertificateSerializer,
    CertificateVerifySerializer,
)
from .services import CertificateService


class CertificateListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/certificates/  — Lister mes certificats
    POST /api/certificates/  — Créer un certificat (admin uniquement)

    GET :
        - Apprenant : voit uniquement SES certificats
        - Admin     : voit TOUS les certificats

    POST :
        Réservé aux administrateurs (création manuelle).
        Corps JSON attendu :
            {
                "user_id": "uuid-de-l-utilisateur",
                "formation_id": 5
            }
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CertificateCreateSerializer
        return CertificateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_administrateur:
            return Certificate.objects.select_related('user', 'formation').all()
        return Certificate.objects.select_related('formation').filter(user=user)

    def create(self, request, *args, **kwargs):
        """Création manuelle par un admin."""
        if not request.user.is_administrateur:
            return Response(
                {'detail': "Seuls les administrateurs peuvent créer des certificats."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CertificateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            certificate = CertificateService.create_certificate(
                user=serializer.user,
                formation=serializer.formation,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        result = CertificateSerializer(certificate)
        return Response(result.data, status=status.HTTP_201_CREATED)


class CertificateDetailView(generics.RetrieveAPIView):
    """
    GET /api/certificates/<id>/
    Détail d'un certificat.
    L'apprenant ne voit que ses propres certificats.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CertificateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_administrateur:
            return Certificate.objects.select_related('user', 'formation').all()
        return Certificate.objects.select_related('formation').filter(user=user)


class CertificateDownloadView(APIView):
    """
    GET /api/certificates/<id>/download/
    Télécharge le fichier PDF du certificat.

    AMBIGUÏTÉ : Pourquoi une vue séparée au lieu de retourner l'URL du PDF dans le serializer ?
      - L'URL du PDF dans le serializer nécessite que le client fasse un GET sur l'URL media
      - Cette vue permet de :
        1. Vérifier les permissions AVANT de donner accès au fichier
        2. Forcer le téléchargement (Content-Disposition: attachment)
        3. Gérer le cas où le PDF n'a pas encore été généré (régénération à la volée)
      - En production, on pourrait servir le PDF directement via nginx (X-Sendfile)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            if request.user.is_administrateur:
                certificate = Certificate.objects.get(pk=pk)
            else:
                certificate = Certificate.objects.get(pk=pk, user=request.user)
        except Certificate.DoesNotExist:
            return Response(
                {'detail': "Certificat introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not certificate.pdf_file:
            # Régénérer le PDF s'il n'existe pas
            from .services import PDFGenerator
            PDFGenerator.save_to_model(certificate)

        # Retourner le fichier en téléchargement
        # AMBIGUÏTÉ : Pourquoi lire le fichier en mémoire plutôt que de rediriger vers l'URL media ?
        #   - Le fichier media est accessible publiquement si on connaît l'URL
        #   - En le servant via cette vue, on garantit que seuls les autorisés peuvent télécharger
        #   - En production, on utiliserait X-Sendfile ou X-Accel-Redirect pour éviter
        #     de charger le fichier en mémoire dans Django
        response = Response(content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="{certificate.verification_code}.pdf"'
        )
        response.write(certificate.pdf_file.read())
        return response


class CertificateVerifyView(APIView):
    """
    POST /api/certificates/verify/<code>/
    Vérifie l'authenticité d'un certificat.

    AMBIGUÏTÉ : Pourquoi POST et pas GET ?
      - GET serait plus RESTful pour une opération de "lecture"
      - Mais POST permet de passer le code dans le body (plus propre)
      - Et POST évite que le code ne se retrouve dans les logs du serveur (URL = loguée)
      - En pratique, GET fonctionnerait aussi bien. On pourrait changer.

    Permission : AllowAny
      - N'importe qui peut vérifier un certificat (employeurs, institutions)
      - Seules les infos publiques sont retournées (pas de données sensibles)
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, code):
        result = CertificateService.verify_certificate(code)
        serializer = CertificateVerifySerializer(result)
        status_code = status.HTTP_200_OK if result['is_valid'] else status.HTTP_404_NOT_FOUND
        return Response(serializer.data, status=status_code)

    # On supporte aussi GET pour faciliter l'intégration
    def get(self, request, code):
        return self.post(request, code)
