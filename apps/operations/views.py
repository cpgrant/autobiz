from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse


def home(request):
    return HttpResponse(
        """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Autobiz</title></head>
<body><main><h1>Autobiz</h1><p>Controlled business foundation is running.</p>
<ul><li><a href=\"/health/\">Health</a></li><li><a href=\"/ready/\">Readiness</a></li>
<li><a href=\"/admin/\">Django admin</a></li></ul></main></body></html>"""
    )


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
