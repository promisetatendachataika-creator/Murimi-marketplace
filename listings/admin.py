from django.contrib import admin
from django.utils.html import format_html

from .models import Listing, ListingPhoto


class PhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0
    fields = ["preview", "image", "position"]
    readonly_fields = ["preview"]

    @admin.display(description="Photo")
    def preview(self, obj):
        return format_html('<img src="{}" style="height:70px;border-radius:6px">', obj.image.url) if obj.pk else ""


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    """Staff moderation: find listings, hide bad ones, put them back."""

    list_display = ["id", "crop", "variety", "farmer", "province", "price_usd", "quantity_left", "quantity",
                    "status", "available_from", "sell_today", "created_at"]
    list_filter = ["status", "crop", "province", "sell_today", "farmer__is_verified_farmer"]
    search_fields = ["crop", "variety", "district", "description", "farmer__name", "farmer__phone"]
    list_select_related = ["farmer"]
    raw_id_fields = ["farmer"]
    date_hierarchy = "created_at"
    inlines = [PhotoInline]
    actions = ["hide", "show_again"]

    @admin.action(description="Hide from the market")
    def hide(self, request, queryset):
        n = queryset.update(status=Listing.HIDDEN)
        self.message_user(request, f"{n} listing(s) hidden.")

    @admin.action(description="Put back on the market")
    def show_again(self, request, queryset):
        n = queryset.filter(status=Listing.HIDDEN).update(status=Listing.ACTIVE)
        self.message_user(request, f"{n} listing(s) back on the market.")
