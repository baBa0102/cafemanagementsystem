from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ItemCategory(TimeStampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Item Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class Item(TimeStampedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='items/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(ItemCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')

    def __str__(self):
        return self.name


class Customer(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def total_spent(self):
        from django.db.models import Sum
        agg = self.orders.aggregate(s=Sum('total_amount'))
        return agg.get('s') or 0

    @property
    def items_purchased_count(self):
        return sum(oi.quantity for o in self.orders.all() for oi in o.items.all())


class Address(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='India')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.line1}, {self.city}"


class Cart(TimeStampedModel):
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('CHECKED_OUT', 'Checked Out'),
    )
    session_key = models.CharField(max_length=40, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name='carts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')

    def __str__(self):
        return f"Cart {self.id} ({self.status})"

    @property
    def total(self):
        return sum((ci.subtotal for ci in self.items.all()), start=0)


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('cart', 'item')

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Order(TimeStampedModel):
    ORDER_TYPE_CHOICES = (
        ('DINING', 'Dining'),
        ('DELIVERY', 'Delivery'),
    )
    STATUS_CHOICES = (
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('PAID', 'Paid'),
        ('PREPARING', 'Preparing'),
        ('READY_FOR_DELIVERY', 'Ready for Delivery'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('COMPLETED', 'Completed'),
        ('CANCELED', 'Canceled'),
        ('REJECTED', 'Rejected'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='orders')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    table_no = models.CharField(max_length=20, blank=True)  # only for dining
    delivery_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT')
    sent_to_chef_at = models.DateTimeField(null=True, blank=True)
    preparing_started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.order_type} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Payment(TimeStampedModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('FAILED', 'Failed'),
    )
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    verified_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Payment for Order #{self.order_id} - {self.status}"


class PaymentConfig(TimeStampedModel):
    upi_id = models.CharField(max_length=100, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    qr_code = models.ImageField(upload_to='payments/', blank=True, null=True)

    class Meta:
        verbose_name = 'Payment Configuration'
        verbose_name_plural = 'Payment Configuration'

    def __str__(self):
        return 'Payment Configuration'


class Offer(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    percent_off = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    amount_off = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class WishlistItem(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wishlist_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('customer', 'item')

    def __str__(self):
        return f"{self.customer} - {self.item}"
