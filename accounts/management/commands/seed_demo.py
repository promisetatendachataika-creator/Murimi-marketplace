"""
python manage.py seed_demo

Creates the demo accounts the front end's sample data uses, so log-in works for real:
  Tendai Moyo   077 123 4567 / tendai / tendai@example.com   password murimi2026   sells and buys, Murimi Verified
  Rudo Buyer    071 234 5678 / rudo                          password murimi2026   buyer
  Staff         078 000 0000                                 password murimi-staff-2026  (for /admin/)
Safe to run again: existing accounts are left as they are.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User

DEMO = [
    dict(phone="+263771234567", name="Tendai Moyo", username="tendai", email="tendai@example.com",
         role="both", is_verified_farmer=True, password="murimi2026"),
    dict(phone="+263712345678", name="Rudo Buyer", username="rudo", email=None, role="buyer", password="murimi2026"),
]


class Command(BaseCommand):
    help = "Create demo accounts (Tendai, Rudo, and a staff login)."

    def handle(self, *args, **opts):
        now = timezone.now()
        for d in DEMO:
            d = dict(d)
            password = d.pop("password")
            if User.objects.filter(phone=d["phone"]).exists():
                self.stdout.write(f"  exists: {d['name']}")
                continue
            User.objects.create_user(password=password, phone_verified_at=now,
                                     verified_farmer_on=timezone.localdate() if d.get("is_verified_farmer") else None, **d)
            self.stdout.write(self.style.SUCCESS(f"  created: {d['name']} ({d['phone']})"))
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(phone="+263780000000", password="murimi-staff-2026", name="Murimi staff")
            self.stdout.write(self.style.SUCCESS("  created: staff log-in 078 000 0000 (for /admin/)"))
        self.stdout.write("Done. Change the staff password before going live.")
