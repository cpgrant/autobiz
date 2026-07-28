import pytest
from django.contrib.auth import get_user_model

from apps.operations.models import Customer, Engagement, Product, WorkflowRun


@pytest.fixture
def operator(db):
    return get_user_model().objects.create_user(username="operator", password="test-password")


@pytest.fixture
def workflow_run(db):
    customer = Customer.objects.create(name="Example Consultancy")
    product = Product.objects.create(
        key="foundation-control",
        name="Foundation Control",
        promised_outcome="Exercise generic control primitives.",
    )
    engagement = Engagement.objects.create(customer=customer, product=product)
    return WorkflowRun.objects.create(engagement=engagement, workflow_key="control-check")
