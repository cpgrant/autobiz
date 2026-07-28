from django.urls import reverse


def test_home_page_links_to_operational_endpoints(client):
    response = client.get(reverse("home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Autobiz" in content
    assert 'href="/health/"' in content
    assert 'href="/ready/"' in content
    assert 'href="/admin/"' in content
