"""
Seed script: creates test users across roles with a consistent username format.

Usage:
    python manage.py seed_users

Username format: pkl-firstname.lastname (lowercase)
Default password for all seeded users: Pathcare@2026
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

DEFAULT_PASSWORD = "Pathcare@2026"

FIRST_NAMES = [
    "James", "Mary", "John", "Grace", "Peter", "Faith", "David", "Joyce",
    "Daniel", "Ann", "Samuel", "Ruth", "Joseph", "Alice", "Michael", "Esther",
    "Paul", "Beatrice", "Stephen", "Catherine", "George", "Lucy", "Francis",
    "Nancy", "Anthony", "Jane", "Patrick", "Winnie", "Kevin", "Susan",
    "Brian", "Mercy", "Dennis", "Sharon", "Charles", "Irene", "Robert",
    "Christine", "Simon", "Diana", "Vincent", "Agnes", "Edwin", "Purity",
    "Moses", "Eunice", "Isaac", "Caroline", "Felix", "Rose", "Kennedy",
    "Judith", "Collins", "Josephine", "Eric", "Naomi", "Martin", "Elizabeth",
]

LAST_NAMES = [
    "Mwangi", "Wanjiru", "Otieno", "Achieng", "Kariuki", "Njoroge", "Kamau",
    "Wambui", "Odhiambo", "Auma", "Kipchoge", "Chebet", "Mutua", "Nduta",
    "Omondi", "Adhiambo", "Njuguna", "Wairimu", "Ochieng", "Akinyi",
    "Kimani", "Nyambura", "Barasa", "Nafula", "Cheruiyot", "Jepkosgei",
    "Maina", "Muthoni", "Owino", "Atieno", "Rotich", "Jelagat", "Gitau",
    "Waithera", "Onyango", "Awuor", "Koech", "Chepkoech", "Macharia",
    "Wangari", "Osoro", "Kerubo", "Langat", "Cherotich", "Wanyama",
    "Nekesa", "Simiyu", "Naliaka", "Too", "Chelangat",
]

ROLE_COUNTS = {
    "client": 30,
    "carrier": 10,
    "dispatcher": 3,
    "lab_staff": 10,
}


class Command(BaseCommand):
    help = "Seed test users across roles (clients, carriers, dispatchers, lab staff)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without saving to the database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        used_usernames = set(User.objects.values_list("username", flat=True))
        used_name_pairs = set()

        created_count = 0

        with transaction.atomic():
            self._ensure_super_admin(dry_run, used_usernames)
            for role, count in ROLE_COUNTS.items():
                self.stdout.write(self.style.NOTICE(f"\nSeeding {count} {role} users..."))

                for _ in range(count):
                    first, last, username = self._generate_unique_identity(
                        used_name_pairs, used_usernames
                    )
                    email = f"{first.lower()}.{last.lower()}@example.com"
                    phone = f"07{random.randint(10000000, 99999999)}"

                    if dry_run:
                        self.stdout.write(f"  [dry-run] {username} | {first} {last} | {role}")
                        continue

                    user = User(
                        username=username,
                        first_name=first,
                        last_name=last,
                        email=email,
                        role=role,
                        is_active=True,
                    )
                    # set phone only if the field exists on the model
                    if hasattr(user, "phone"):
                        user.phone = phone

                    user.set_password(DEFAULT_PASSWORD)
                    user.save()
                    created_count += 1
                    self.stdout.write(f"  Created: {username} ({role})")

            if dry_run:
                self.stdout.write(self.style.WARNING("\nDry run complete — no users were created."))
                # roll back the transaction since nothing should persist in dry-run mode
                transaction.set_rollback(True)
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nDone. Created {created_count} users. "
                        f"Default password for all: {DEFAULT_PASSWORD}"
                    )
                )

    def _ensure_super_admin(self, dry_run, used_usernames):
        """Ensure a seeded super-admin account exists without changing the existing role logic."""
        username = "pkl-super.admin"
        existing_user = User.objects.filter(username=username).first()

        if existing_user:
            if existing_user.is_super_admin() and existing_user.role == User.Role.SUPER_ADMIN:
                used_usernames.add(username)
                return

            if dry_run:
                self.stdout.write(f"  [dry-run] {username} | Super Admin | super_admin")
                return

            existing_user.role = User.Role.SUPER_ADMIN
            existing_user.is_superuser = True
            existing_user.is_staff = True
            existing_user.save(update_fields=["role", "is_superuser", "is_staff"])
            used_usernames.add(username)
            self.stdout.write(f"  Updated: {username} (super_admin)")
            return

        if username in used_usernames:
            return

        if dry_run:
            self.stdout.write(f"  [dry-run] {username} | Super Admin | super_admin")
            return

        User.objects.create_superuser(
            username=username,
            first_name="Super",
            last_name="Admin",
            email="super.admin@example.com",
            password=DEFAULT_PASSWORD,
        )
        used_usernames.add(username)
        self.stdout.write(f"  Created: {username} (super_admin)")

    def _generate_unique_identity(self, used_name_pairs, used_usernames):
        """Generate a unique first/last name pair and derived username."""
        while True:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            if (first, last) in used_name_pairs:
                continue

            username = f"pkl-{first.lower()}.{last.lower()}"
            if username in used_usernames:
                continue

            used_name_pairs.add((first, last))
            used_usernames.add(username)
            return first, last, username