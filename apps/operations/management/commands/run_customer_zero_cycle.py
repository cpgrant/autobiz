from django.core.management.base import BaseCommand

from apps.operations.cycle_services import run_daily_cycle
from apps.operations.models import Company


class Command(BaseCommand):
    help = "Run the next deterministic Customer Zero synthetic operating day."

    def handle(self, *args, **options):
        company = Company.objects.get(key="autobiz")
        result = run_daily_cycle(company=company, actor="operator:management-command")
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed {result.cycle.operating_date}; simulated "
                f"{result.internal_actions_simulated} bounded action and requested "
                f"{result.approvals_requested} approval."
            )
        )
