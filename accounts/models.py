"""
Accounts tables.

User       one row per person. Log in with WhatsApp number, username or email.
PhoneCode  6-digit WhatsApp codes. Only an HMAC fingerprint of the code is stored,
           never the code itself (same rule as the Hub).
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .choices import BUSINESS_CHOICES, ROLE_BOTH, ROLE_BUYER, ROLE_CHOICES, ROLE_FARMER  # noqa: F401
from .phone import normalize_phone, try_normalize_phone


class UserManager(BaseUserManager):
    """How Django creates users (also used by `createsuperuser`)."""

    use_in_migrations = True

    def create_user(self, phone, password=None, **extra):
        phone = normalize_phone(phone)
        if extra.get("email"):
            extra["email"] = self.normalize_email(extra["email"]).lower()
        if extra.get("username"):
            extra["username"] = extra["username"].strip().lower()
        user = self.model(phone=phone, **extra)
        user.set_password(password)          # stores a salted hash, never the password
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("phone_verified_at", timezone.now())
        extra.setdefault("name", "Murimi staff")
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    # USERNAME_FIELD is the one unique field Django treats as "the login name".
    phone = models.CharField("WhatsApp number", max_length=16, unique=True,
                             help_text="Stored as +2637XXXXXXXX.")
    username = models.CharField(max_length=30, unique=True, null=True, blank=True,
                                help_text="Optional. Lower-case letters, numbers and _ only.")
    email = models.EmailField(unique=True, null=True, blank=True, help_text="Optional.")
    name = models.CharField(max_length=60)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=True,
                            help_text="Blank for staff.")
    business_type = models.CharField(
        "Business", max_length=20, choices=BUSINESS_CHOICES, blank=True,
        help_text="Leave blank for a person. For a shop, school, hotel... the full name is shown.")
    phone_verified_at = models.DateTimeField(null=True, blank=True,
                                             help_text="When the WhatsApp code was confirmed.")
    is_verified_farmer = models.BooleanField(
        "Murimi Verified", default=False,
        help_text="Set by staff after a field officer has checked the farm, ID and land.")
    verified_farmer_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True,
                                    help_text="Off until the WhatsApp code is confirmed, or if staff block the account.")
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]          # asked for by `createsuperuser`

    class Meta:
        ordering = ["-date_joined"]

    def clean(self):
        """Checked by every form, including the staff screen in /admin/."""
        super().clean()
        if self.phone and not try_normalize_phone(self.phone):
            raise ValidationError({"phone": "Enter a Zimbabwe mobile number, like 077 123 4567 or +263 77 123 4567."})

    def save(self, *args, **kwargs):
        """One form for everything we search by, whichever screen the account came from.

        The phone is stored as +2637XXXXXXXX however it was typed. Without this, an account
        added in /admin/ keeps the raw "0771234567", and then nobody can log in as them:
        logging in normalises what is typed and looks for the +263 form, which isn't there.
        Username and email are lower-cased, and empty becomes NULL (not "", because UNIQUE
        allows many NULLs but only one "").
        """
        self.phone = try_normalize_phone(self.phone) or self.phone
        self.username = (self.username or "").strip().lower() or None
        self.email = (self.email or "").strip().lower() or None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def can_sell(self):
        return self.role in (ROLE_FARMER, ROLE_BOTH)

    @property
    def can_buy(self):
        return self.role in (ROLE_BUYER, ROLE_BOTH)

    def public_name(self):
        """What other people see: first name and last initial, e.g. "Tendai M."."""
        if self.business_type:                       # "FreshMart", "Mzilikazi High School": shown in full
            return self.name
        parts = self.name.split()
        return f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else self.name

    def as_json(self):
        """The logged-in user's own details, for /api/auth/me/."""
        return {
            "id": self.id, "name": self.name, "phone": self.phone,
            "username": self.username or "", "email": self.email or "", "role": self.role,
            "is_verified_farmer": self.is_verified_farmer, "is_staff": self.is_staff,
            # What this account may DO. The pages hide buttons for anything that is False,
            # so nobody fills in a form only to be refused. The server checks again anyway.
            "can_sell": self.can_sell, "can_buy": self.can_buy,
        }


class PhoneCode(models.Model):
    """A 6-digit code sent by WhatsApp, to confirm a number (register) or reset a password."""

    PURPOSE_REGISTER = "register"
    PURPOSE_RESET = "reset"
    PURPOSES = [(PURPOSE_REGISTER, "Confirm number"), (PURPOSE_RESET, "Reset password")]

    LIFETIME = timedelta(minutes=10)
    MAX_ATTEMPTS = 5

    phone = models.CharField(max_length=16, db_index=True)
    purpose = models.CharField(max_length=10, choices=PURPOSES)
    code_hash = models.CharField(max_length=64)      # HMAC-SHA256 fingerprint, never the code
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["phone", "purpose", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_purpose_display()} code for {self.phone}"

    @staticmethod
    def fingerprint(phone, code):
        """HMAC with the secret key: even someone who copies the database can't read codes."""
        key = settings.SECRET_KEY.encode()
        return hmac.new(key, f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()

    @classmethod
    def issue(cls, phone, purpose):
        """Make a new code (older unused ones for the same purpose stop working). Returns the plain code."""
        code = f"{secrets.randbelow(1_000_000):06d}"
        now = timezone.now()
        cls.objects.filter(phone=phone, purpose=purpose, used_at__isnull=True).update(used_at=now)
        cls.objects.create(phone=phone, purpose=purpose, code_hash=cls.fingerprint(phone, code),
                           expires_at=now + cls.LIFETIME)
        return code

    @classmethod
    def verify_code(cls, phone, purpose, code):
        """True if `code` is the latest, unexpired, unused code. Counts wrong tries."""
        row = cls.objects.filter(phone=phone, purpose=purpose, used_at__isnull=True).first()
        if not row or row.expires_at < timezone.now() or row.attempts >= cls.MAX_ATTEMPTS:
            return False
        if not hmac.compare_digest(row.code_hash, cls.fingerprint(phone, code)):
            row.attempts += 1
            row.save(update_fields=["attempts"])
            return False
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])
        return True
