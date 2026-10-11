from django.core.management.base import BaseCommand
from Canteen_backend.order_flow import sweep_pending_orders


class Command(BaseCommand):
    help = "Promote eligible pending orders to preparing across all canteens"

    def handle(self, *args, **options):
        promoted = sweep_pending_orders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully swept pending orders. Promoted {len(promoted)} orders."
            )
        )
