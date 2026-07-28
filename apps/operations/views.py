from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok", "service": "autobiz"})


def readiness(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse(
            {"status": "not_ready", "service": "autobiz", "database": "unavailable"},
            status=503,
        )
    return JsonResponse({"status": "ready", "service": "autobiz", "database": "ok"})
