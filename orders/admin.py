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
    date_hierarchy = "created_at"
    inlines = [RatingInline]
    list_select_related = ["buyer", "farmer"]

    # Staff READ orders (to settle a dispute) but never edit them: an agreed price or quantity
    # that staff could change would make every deal untrustworthy. Stock is changed only by accept.
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["order", "by_user", "for_user", "stars", "comment", "created_at"]
    list_filter = ["stars"]
    search_fields = ["by_user__name", "for_user__name", "comment"]
    raw_id_fields = ["order", "by_user", "for_user"]

    def has_add_permission(self, request):
        return False                       # ratings only come from real completed orders
