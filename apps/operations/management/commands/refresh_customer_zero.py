from django.core.management.base import BaseCommand

from apps.operations.models import Company
from apps.operations.services import refresh_company_state


class Command(BaseCommand):
    help = "Refresh deterministic Customer Zero metrics and work priorities."

    def handle(self, *args, **options):
        company = Company.objects.get(key="autobiz")
        result = refresh_company_state(
            company=company,
            actor="operator:management-command",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Refreshed {result.metrics_updated} metrics and prioritized "
                f"{result.work_items_prioritized} work items."
            )
        )
