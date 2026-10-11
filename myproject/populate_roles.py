import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from django.contrib.auth.models import User, Group
from Canteen_backend.models import UserProfile

def populate():
    staff_group, _ = Group.objects.get_or_create(name="Staff")
    admin_group, _ = Group.objects.get_or_create(name="Admin")
    print("Ensured Groups 'Staff' and 'Admin' exist.")

    users = User.objects.all().order_by("id")
    print(f"Found {users.count()} existing users.")

    for u in users:
        uname = u.username.lower()
        if uname in ["admin", "testadmin"] or u.is_superuser:
            role = "admin"
        elif uname == "deepak":
            role = "staff"
        else:
            role = "user"

        profile, created = UserProfile.objects.get_or_create(user=u, defaults={"role": role})
        if not created and profile.role != role:
            profile.role = role
            profile.save()

        if role == "staff":
            u.groups.add(staff_group)
            print(f"User '{u.username}' (id={u.id}) configured with role='staff' and added to 'Staff' group.")
        elif role == "admin":
            u.groups.add(admin_group)
            print(f"User '{u.username}' (id={u.id}) configured with role='admin'.")
        else:
            u.groups.remove(staff_group)
            print(f"User '{u.username}' (id={u.id}) configured with role='user'.")

    print("User profiles populated successfully!")

if __name__ == "__main__":
    populate()
