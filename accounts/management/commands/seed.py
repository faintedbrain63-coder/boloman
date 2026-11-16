from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from allauth.account.models import EmailAddress

from accounts.models import CustomerProfile

PASSWORD = "Admin2026!"

USERS = [
    {
        "username": "admin",
        "email": "admin@boloman.ph",
        "first_name": "Boloman",
        "last_name": "Admin",
        "is_staff": True,
        "is_superuser": True,
        "phone": "09171234567",
        "address_line": "123 Print Street",
        "city": "Quezon City",
        "province": "Metro Manila",
        "postal_code": "1100",
    },
    {
        "username": "maya.santos",
        "email": "maya.santos@boloman.ph",
        "first_name": "Maya",
        "last_name": "Santos",
        "is_staff": True,
        "is_superuser": False,
        "phone": "09181230001",
        "address_line": "88 Production Road",
        "city": "Quezon City",
        "province": "Metro Manila",
        "postal_code": "1101",
    },
    {
        "username": "leo.reyes",
        "email": "leo.reyes@boloman.ph",
        "first_name": "Leo",
        "last_name": "Reyes",
        "is_staff": True,
        "is_superuser": False,
        "phone": "09181230002",
        "address_line": "14 Warehouse Lane",
        "city": "Pasig",
        "province": "Metro Manila",
        "postal_code": "1600",
    },
    {
        "username": "ana.cruz",
        "email": "ana.cruz@example.com",
        "first_name": "Ana",
        "last_name": "Cruz",
        "is_staff": False,
        "is_superuser": False,
        "phone": "09171230011",
        "address_line": "45 Mabini Street",
        "city": "Manila",
        "province": "Metro Manila",
        "postal_code": "1000",
    },
    {
        "username": "marco.delacruz",
        "email": "marco.delacruz@example.com",
        "first_name": "Marco",
        "last_name": "Dela Cruz",
        "is_staff": False,
        "is_superuser": False,
        "phone": "09171230012",
        "address_line": "9 Katipunan Avenue",
        "city": "Quezon City",
        "province": "Metro Manila",
        "postal_code": "1108",
    },
    {
        "username": "isla.navarro",
        "email": "isla.navarro@example.com",
        "first_name": "Isla",
        "last_name": "Navarro",
        "is_staff": False,
        "is_superuser": False,
        "phone": "09171230013",
        "address_line": "220 Shaw Boulevard",
        "city": "Mandaluyong",
        "province": "Metro Manila",
        "postal_code": "1552",
    },
    {
        "username": "paolo.gomez",
        "email": "paolo.gomez@example.com",
        "first_name": "Paolo",
        "last_name": "Gomez",
        "is_staff": False,
        "is_superuser": False,
        "phone": "09171230014",
        "address_line": "3 Session Road",
        "city": "Baguio",
        "province": "Benguet",
        "postal_code": "2600",
    },
    {
        "username": "rina.bautista",
        "email": "rina.bautista@example.com",
        "first_name": "Rina",
        "last_name": "Bautista",
        "is_staff": False,
        "is_superuser": False,
        "phone": "09171230015",
        "address_line": "77 Ayala Avenue",
        "city": "Makati",
        "province": "Metro Manila",
        "postal_code": "1226",
    },
]


class Command(BaseCommand):
    help = "Create Boloman staff and customer accounts. Every user password is set to Admin2026!."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        seeded_ids = []
        created_count = 0
        for spec in USERS:
            user, created = self._upsert(User, spec)
            self._profile(user, spec)
            self._email(user, spec["email"])
            seeded_ids.append(user.pk)
            created_count += int(created)
            role = "admin" if spec["is_superuser"] else "staff" if spec["is_staff"] else "customer"
            self.stdout.write(f"{'Created' if created else 'Updated'} {role}: {spec['email']}")

        others = User.objects.exclude(pk__in=seeded_ids)
        reset_count = 0
        for user in others:
            user.set_password(PASSWORD)
            user.save(update_fields=["password"])
            reset_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(USERS)} users ({created_count} new). Password for all {User.objects.count()} users is {PASSWORD}."
        ))
        if reset_count:
            self.stdout.write(f"Also reset the password on {reset_count} existing user(s) outside this list.")

    def _upsert(self, User, spec):
        user = User.objects.filter(email__iexact=spec["email"]).first()
        if user is None:
            user = User.objects.filter(username=spec["username"]).first()
        created = user is None
        if created:
            user = User(username=spec["username"])
        elif user.username != spec["username"] and not User.objects.exclude(pk=user.pk).filter(username=spec["username"]).exists():
            user.username = spec["username"]
        user.email = spec["email"]
        user.first_name = spec["first_name"]
        user.last_name = spec["last_name"]
        user.is_staff = spec["is_staff"]
        user.is_superuser = spec["is_superuser"]
        user.is_active = True
        user.set_password(PASSWORD)
        user.save()
        return user, created

    def _profile(self, user, spec):
        profile, _created = CustomerProfile.objects.get_or_create(user=user)
        profile.phone = spec["phone"]
        profile.address_line = spec["address_line"]
        profile.city = spec["city"]
        profile.province = spec["province"]
        profile.postal_code = spec["postal_code"]
        profile.save()

    def _email(self, user, email):
        address, _created = EmailAddress.objects.get_or_create(
            user=user,
            email=email.lower(),
            defaults={"verified": True, "primary": True},
        )
        address.verified = True
        address.primary = True
        address.save(update_fields=["verified", "primary"])
        EmailAddress.objects.filter(user=user).exclude(pk=address.pk).update(primary=False)
