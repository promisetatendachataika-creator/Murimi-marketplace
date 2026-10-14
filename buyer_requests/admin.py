from django.contrib import admin

from .models import BuyerRequest


@admin.register(BuyerRequest)
class BuyerRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "crop", "quantity", "unit", "buyer", "province", "needed_by", "repeat", "status"]
    list_filter = ["status", "crop", "province", "repeat"]
    search_fields = ["id", "buyer__name", "buyer__phone", "district", "note"]
    raw_id_fields = ["buyer"]
    actions = ["close_requests"]

    @admin.action(description="Close the selected requests")
    def close_requests(self, request, queryset):
        n = queryset.update(status=BuyerRequest.CLOSED)
        self.message_user(request, f"{n} request(s) closed.")
