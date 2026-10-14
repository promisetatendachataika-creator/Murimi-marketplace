from django.contrib import admin

from .models import Order, Rating


class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    fields = ["by_user", "for_user", "stars", "comment", "created_at"]
    readonly_fields = fields
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "crop", "quantity", "unit", "price_usd", "buyer", "farmer", "proposed_by", "status", "created_at"]
    list_filter = ["status", "proposed_by", "crop"]
    search_fields = ["id", "buyer__name", "buyer__phone", "farmer__name", "farmer__phone"]
    raw_id_fields = ["listing", "request", "farmer", "buyer"]
    readonly_fields = ["created_at", "accepted_at", "completed_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [RatingInline]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["order", "by_user", "for_user", "stars", "comment", "created_at"]
    list_filter = ["stars"]
    search_fields = ["by_user__name", "for_user__name", "comment"]
    raw_id_fields = ["order", "by_user", "for_user"]
