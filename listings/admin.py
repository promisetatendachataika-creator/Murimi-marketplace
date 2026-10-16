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

    list_display = ["id", "photo", "product", "variety", "farmer", "province", "price_usd", "quantity_left",
                    "status", "open_reports", "told_us", "created_at"]
    list_filter = ["status", "crop", "province", "sell_today", "farmer__is_verified_farmer"]
    search_fields = ["crop", "variety", "district", "description", "farmer__name", "farmer__phone"]
    list_select_related = ["farmer"]
    raw_id_fields = ["farmer"]
    date_hierarchy = "created_at"
    inlines = [PhotoInline]
    actions = ["approve_product", "decline_product", "hide", "show_again"]

    @admin.display(description="Product", ordering="crop")
    def product(self, obj):
        """Shows what the farmer typed when they chose "Other"."""
        return format_html('{} <b>{}</b>', "NEW:", obj.other_product) if obj.other_product else obj.crop

    def get_queryset(self, request):
        """Photos come along too, so the list can show them without a query per row."""
        return (super().get_queryset(request)
                .annotate(_open_reports=Count("reports", filter=Q(reports__status="open")))
                .prefetch_related("photos"))

    @admin.display(description="Photo")
    def photo(self, obj):
        """You can't judge produce you can't see, so the first photo is in the list itself."""
        first = obj.photos.all()[:1]
        if not first:
            return format_html('<span style="color:#b4561f">no photo</span>')
        return format_html('<a href="{}" target="_blank"><img src="{}" style="height:46px;width:62px;'
                           'object-fit:cover;border-radius:5px"></a>', first[0].image.url, first[0].image.url)

    @admin.display(description="What the farmer says")
    def told_us(self, obj):
        text = obj.description or ""
        return format_html('<span title="{}">{}</span>', text, (text[:60] + "...") if len(text) > 60 else text or "-")

    @admin.display(description="Reports", ordering="_open_reports")
    def open_reports(self, obj):
        return obj._open_reports or ""

    @admin.action(description='Approve this new product and put the listing on the market')
    def approve_product(self, request, queryset):
        waiting = queryset.filter(status=Listing.REVIEW)
        names = sorted({l.other_product for l in waiting if l.other_product})
        n = waiting.update(status=Listing.ACTIVE)
        self.message_user(request, f"{n} listing(s) now on the market."
                                   + (f" New products: {', '.join(names)}." if names else ""))

    @admin.action(description="Decline this new product (the farmer keeps it as a draft)")
    def decline_product(self, request, queryset):
        n = queryset.filter(status=Listing.REVIEW).update(status=Listing.DRAFT)
        self.message_user(request, f"{n} listing(s) sent back to the farmer as a draft. "
                                   "WhatsApp them to say why.")

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
