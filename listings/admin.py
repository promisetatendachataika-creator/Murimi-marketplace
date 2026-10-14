from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from .models import Listing, ListingPhoto, ListingReport


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
                    "status", "open_reports", "available_from", "created_at"]
    list_filter = ["status", "crop", "province", "sell_today", "farmer__is_verified_farmer"]
    search_fields = ["crop", "variety", "district", "description", "farmer__name", "farmer__phone"]
    list_select_related = ["farmer"]
    raw_id_fields = ["farmer"]
    date_hierarchy = "created_at"
    inlines = [PhotoInline]
    actions = ["hide", "show_again"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_open_reports=Count("reports", filter=Q(reports__status="open")))

    @admin.display(description="Reports", ordering="_open_reports")
    def open_reports(self, obj):
        return obj._open_reports or ""

    @admin.action(description="Hide from the market")
    def hide(self, request, queryset):
        n = queryset.update(status=Listing.HIDDEN)
        self.message_user(request, f"{n} listing(s) hidden.")

    @admin.action(description="Put back on the market")
    def show_again(self, request, queryset):
        n = queryset.filter(status=Listing.HIDDEN).update(status=Listing.ACTIVE)
        self.message_user(request, f"{n} listing(s) back on the market.")


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    """The staff queue: people flagging listings. Hide the listing, or mark the report handled."""

    list_display = ["id", "status", "reason", "listing", "listing_status", "reporter", "details", "created_at"]
    list_filter = ["status", "reason"]
    search_fields = ["details", "listing__crop", "listing__farmer__name", "reporter__name", "reporter__phone"]
    list_select_related = ["listing", "listing__farmer", "reporter"]
    raw_id_fields = ["listing", "reporter"]
    readonly_fields = ["listing", "reporter", "reason", "details", "created_at", "handled_by", "handled_at"]
    fields = ["listing", "reporter", "reason", "details", "created_at", "status", "outcome", "handled_by", "handled_at"]
    actions = ["hide_and_close", "close_no_action"]

    def has_add_permission(self, request):
        return False                       # reports come from the site, not from staff typing them in

    @admin.display(description="Listing is")
    def listing_status(self, obj):
        return obj.listing.get_status_display()

    def save_model(self, request, obj, form, change):
        if obj.status == ListingReport.DONE and not obj.handled_at:
            obj.handled_by, obj.handled_at = request.user, timezone.now()
        super().save_model(request, obj, form, change)

    def _close(self, request, queryset, outcome):
        n = queryset.filter(status=ListingReport.OPEN).update(
            status=ListingReport.DONE, handled_by=request.user, handled_at=timezone.now(), outcome=outcome)
        return n

    @admin.action(description="Hide the listing from the market and mark handled")
    def hide_and_close(self, request, queryset):
        ids = list(queryset.filter(status=ListingReport.OPEN).values_list("listing_id", flat=True))
        Listing.objects.filter(pk__in=ids, status__in=[Listing.ACTIVE, Listing.SOLD_OUT]).update(status=Listing.HIDDEN)
        # Close every open report on those listings, not just the ticked ones.
        n = self._close(request, ListingReport.objects.filter(listing_id__in=ids), "Listing hidden by staff.")
        self.message_user(request, f"{len(set(ids))} listing(s) hidden, {n} report(s) handled.")

    @admin.action(description="Mark handled (no action needed)")
    def close_no_action(self, request, queryset):
        n = self._close(request, queryset, "Looked at, no action.")
        self.message_user(request, f"{n} report(s) handled.")
