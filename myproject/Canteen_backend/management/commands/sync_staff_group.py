from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from Canteen_backend.models import UserProfile


class Command(BaseCommand):
    help = "Idempotently synchronizes the Django auth 'Staff' group to match UserProfile.role == 'staff'."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the sync and print planned changes without modifying database.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        prefix = "[DRY-RUN] " if dry_run else ""

        if dry_run:
            staff_group = Group.objects.filter(name="Staff").first()
            if not staff_group:
                current_group_user_ids = set()
            else:
                current_group_user_ids = set(staff_group.user_set.values_list("id", flat=True))
        else:
            staff_group, created = Group.objects.get_or_create(name="Staff")
            if created:
                self.stdout.write(self.style.SUCCESS("Created auth Group 'Staff'."))
            current_group_user_ids = set(staff_group.user_set.values_list("id", flat=True))

        # Target: all users whose UserProfile.role is 'staff'
        staff_user_ids = set(
            UserProfile.objects.filter(role="staff").values_list("user_id", flat=True)
        )

        to_add_ids = staff_user_ids - current_group_user_ids
        to_remove_ids = current_group_user_ids - staff_user_ids

        added_count = 0
        removed_count = 0

        if to_add_ids:
            users_to_add = User.objects.filter(id__in=to_add_ids).order_by("username")
            for u in users_to_add:
                if not dry_run:
                    staff_group.user_set.add(u)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{prefix}Added user '{u.username}' (id={u.id}) to 'Staff' group."
                    )
                )
                added_count += 1

        if to_remove_ids:
            users_to_remove = User.objects.filter(id__in=to_remove_ids).order_by("username")
            for u in users_to_remove:
                if not dry_run:
                    staff_group.user_set.remove(u)
                self.stdout.write(
                    self.style.WARNING(
                        f"{prefix}Removed user '{u.username}' (id={u.id}) from 'Staff' group (role is not 'staff')."
                    )
                )
                removed_count += 1

        if added_count == 0 and removed_count == 0:
            self.stdout.write(
                self.style.SUCCESS(f"{prefix}Group 'Staff' is already fully in sync with UserProfile.role.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix}Sync complete: {added_count} user(s) added, {removed_count} user(s) removed."
                )
            )
