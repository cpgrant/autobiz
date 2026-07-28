import pytest

from apps.operations.models import Customer, Engagement, Product, WorkflowRun


@pytest.mark.django_db
def test_workflow_run_defaults_to_pending():
    customer = Customer.objects.create(name="Example Firm")
    product = Product.objects.create(
        key="lead-to-onboarding",
        name="Lead-to-Onboarding Operations",
        promised_outcome="Every eligible enquiry is progressed and visible.",
    )
    engagement = Engagement.objects.create(customer=customer, product=product)

    run = WorkflowRun.objects.create(engagement=engagement, workflow_key="lead-intake")

    assert run.status == WorkflowRun.Status.PENDING
    assert run.attempt_count == 0
    assert str(run) == "lead-intake (pending)"
