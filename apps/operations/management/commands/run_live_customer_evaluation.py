from django.core.management.base import BaseCommand, CommandError

from apps.operations.customer_evaluation import run_customer_evaluation
from apps.operations.models import Company


class Command(BaseCommand):
    help = "Run the synthetic-only OpenAI Customer Loop evaluation suite."

    def add_arguments(self, parser):
        parser.add_argument("--model", default="gpt-5.6-sol")

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(key="autobiz", is_synthetic=True)
        except Company.DoesNotExist as error:
            raise CommandError("Load Customer Zero before running this evaluation.") from error
        evaluation = run_customer_evaluation(
            company=company,
            actor="management-command:live-customer-evaluation",
            live=True,
            model=options["model"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"evaluation={evaluation.pk} status={evaluation.status} "
                f"technical_gate={evaluation.technical_gate_passed} "
                f"cases={evaluation.cases_passed}/{evaluation.cases_total} "
                f"evidence_validity={evaluation.evidence_validity_percent} "
                f"consistency={evaluation.consistency_percent} "
                f"tokens={evaluation.total_input_tokens}/{evaluation.total_output_tokens} "
                f"latency_ms={evaluation.total_latency_ms} "
                f"unauthorized_external_actions={evaluation.unauthorized_external_actions}"
            )
        )
