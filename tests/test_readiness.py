from unittest.mock import MagicMock, patch

import pytest
from django.db.utils import OperationalError
from django.urls import reverse


@pytest.mark.django_db
def test_readiness_reports_database_available(client):
    response = client.get(reverse("readiness"))

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "autobiz", "database": "ok"}


def test_readiness_reports_database_failure(client):
    connection = MagicMock()
    connection.cursor.side_effect = OperationalError("database unavailable")

    with patch.dict("apps.operations.views.connections", {"default": connection}):
        response = client.get(reverse("readiness"))

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "autobiz",
        "database": "unavailable",
    }
