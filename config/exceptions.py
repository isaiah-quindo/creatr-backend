import logging
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Global exception handler for the DRF API.

    Known DRF exceptions (ValidationError, NotAuthenticated, PermissionDenied,
    NotFound, Throttled, MethodNotAllowed, ...) keep DRF's default response
    shape so the frontend's existing `ApiError.data` parsing still works:

        400 validation: {"email": ["This field is required."]}
        401/403/404/etc: {"detail": "..."}

    Anything DRF doesn't recognize would otherwise leak Django's HTML 500 page.
    We log it with a short request id and return JSON instead.
    """
    response = drf_default_handler(exc, context)
    if response is not None:
        return response

    request = context.get("request")
    request_id = uuid.uuid4().hex[:12]
    logger.exception(
        "Unhandled API exception id=%s at %s %s user=%s",
        request_id,
        getattr(request, "method", "?"),
        getattr(request, "path", "?"),
        getattr(getattr(request, "user", None), "pk", None),
    )

    body = {"detail": "Internal server error.", "request_id": request_id}
    if settings.DEBUG:
        body["debug"] = f"{type(exc).__name__}: {exc}"

    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
