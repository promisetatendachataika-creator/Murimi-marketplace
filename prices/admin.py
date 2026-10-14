from django.contrib import admin

from .models import PriceReport


@admin.register(PriceReport)
class PriceReportAdmin(admin.ModelAdmin):
    """Staff type in today's prices from Mbare Musika (or other markets) here."""

    list_display = ["date", "crop", "unit", "price_usd", "price_zig", "market", "created_by"]
    list_filter = ["crop", "market", "date"]
    date_hierarchy = "date"
    search_fields = ["crop", "market", "note"]
    fields = ["date", "crop", "unit", "market", "price_usd", "price_zig", "note"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
