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
    actions = ["mark_verified_farmer", "remove_verified_farmer", "block_accounts", "unblock_accounts"]

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

    @admin.action(description="Take away Murimi Verified")
    def remove_verified_farmer(self, request, queryset):
        n = queryset.update(is_verified_farmer=False, verified_farmer_on=None)
        self.message_user(request, f"{n} account(s) no longer verified.")

    @admin.action(description="Block (can't log in, listings hidden, logged out everywhere)")
    def block_accounts(self, request, queryset):
        from django.contrib.sessions.models import Session
        from listings.models import Listing
        people = list(queryset.exclude(pk=request.user.pk).exclude(is_superuser=True))
        ids = {u.pk for u in people}
        for u in people:
            u.is_active = False
            u.save(update_fields=["is_active"])
        hidden = Listing.objects.filter(farmer_id__in=ids, status=Listing.ACTIVE).update(status=Listing.HIDDEN)
        for s in Session.objects.all():                    # end their sessions now, not in 30 days
            if str(s.get_decoded().get("_auth_user_id")) in {str(i) for i in ids}:
                s.delete()
        self.message_user(request, f"{len(people)} account(s) blocked, {hidden} listing(s) hidden. "
                                   "(Staff and your own account are never blocked from here.)")

    @admin.action(description="Unblock (can log in again; listings stay hidden until you put them back)")
    def unblock_accounts(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} account(s) unblocked.")


@admin.register(PhoneCode)
class PhoneCodeAdmin(admin.ModelAdmin):
    """Read-only: staff can see that codes were sent, never the codes themselves."""

    list_display = ["phone", "purpose", "created_at", "expires_at", "attempts", "used_at"]
    list_filter = ["purpose"]
    search_fields = ["phone"]
    readonly_fields = [f.name for f in PhoneCode._meta.fields]

    def has_add_permission(self, request):
        return False
