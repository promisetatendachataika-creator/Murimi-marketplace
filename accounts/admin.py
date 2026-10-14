from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import PhoneCode, User


class MurimiUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["phone", "name", "role"]


class MurimiUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Staff screen for people. Search by number, name, username or email."""

    form = MurimiUserChangeForm
    add_form = MurimiUserCreationForm
    ordering = ["-date_joined"]
    list_display = ["name", "phone", "username", "email", "role", "is_verified_farmer", "is_active", "date_joined"]
    list_filter = ["role", "is_verified_farmer", "is_active", "is_staff"]
    search_fields = ["phone", "name", "username", "email"]
    readonly_fields = ["date_joined", "last_login", "phone_verified_at"]
    actions = ["mark_verified_farmer", "block_accounts"]

    fieldsets = [
        (None, {"fields": ["phone", "password"]}),
        ("Person", {"fields": ["name", "username", "email", "role", "business_type"]}),
        ("Trust", {"fields": ["phone_verified_at", "is_verified_farmer", "verified_farmer_on"]}),
        ("Access", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["phone", "name", "role", "password1", "password2"]}),
    ]

    @admin.action(description="Mark as Murimi Verified (field officer has visited)")
    def mark_verified_farmer(self, request, queryset):
        n = queryset.update(is_verified_farmer=True, verified_farmer_on=timezone.localdate())
        self.message_user(request, f"{n} account(s) marked Murimi Verified.")

    @admin.action(description="Block (can't log in)")
    def block_accounts(self, request, queryset):
        n = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(request, f"{n} account(s) blocked.")


@admin.register(PhoneCode)
class PhoneCodeAdmin(admin.ModelAdmin):
    """Read-only: staff can see that codes were sent, never the codes themselves."""

    list_display = ["phone", "purpose", "created_at", "expires_at", "attempts", "used_at"]
    list_filter = ["purpose"]
    search_fields = ["phone"]
    readonly_fields = [f.name for f in PhoneCode._meta.fields]

    def has_add_permission(self, request):
        return False
