from django.contrib import admin
from .models import Item, ItemCategory, Customer, Address, Cart, CartItem, Order, OrderItem, PaymentConfig, Offer, WishlistItem, Payment


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "created_at")
    list_editable = ("display_order",)
    search_fields = ("name", "description")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "description")


@admin.register(PaymentConfig)
class PaymentConfigAdmin(admin.ModelAdmin):
    list_display = ("upi_id", "ifsc_code", "account_number", "created_at")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "session_key", "status", "created_at")
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "order_type", "status", "customer", "total_amount", "created_at")
    list_filter = ("status", "order_type")
    inlines = [OrderItemInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "total_spent", "created_at")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "line1", "city", "is_default")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "active", "starts_at", "ends_at")
    list_filter = ("active",)
    search_fields = ("title", "description")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("customer", "item", "created_at")
    list_filter = ("customer",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "status", "reference", "created_at", "verified_at")
    list_filter = ("status",)
    actions = ["mark_verified", "mark_failed"]

    def mark_verified(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for p in queryset:
            p.status = 'VERIFIED'
            p.verified_at = timezone.now()
            p.save()
            # mark order as PAID when payment verified
            p.order.status = 'PAID'
            p.order.save()
            updated += 1
        self.message_user(request, f"Verified {updated} payment(s)")

    def mark_failed(self, request, queryset):
        updated = queryset.update(status='FAILED')
        self.message_user(request, f"Marked {updated} payment(s) as failed")
