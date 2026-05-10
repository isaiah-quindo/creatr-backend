from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import fetch_embed_data


class EmbedPreviewSerializer(serializers.Serializer):
    url = serializers.URLField()


class EmbedPreviewView(APIView):
    """POST a video URL, get back platform + thumbnail + title + embed HTML.

    Used by the dashboard's "Add video" flow to show a preview card before the
    creator confirms and saves the PortfolioItem.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EmbedPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = fetch_embed_data(serializer.validated_data["url"])
        if not data["platform"]:
            return Response(
                {"detail": "Unsupported URL. Use a TikTok, YouTube, or Instagram link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(data)
