from .models import Cart, CartItem, Item
from django.shortcuts import get_object_or_404


def get_or_create_cart(request):
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key
    
    # Try to get existing open cart for this session
    cart = Cart.objects.filter(session_key=session_key, status='OPEN').first()
    
    # If user is authenticated and has a customer profile, link cart to customer
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        if cart:
            # Link existing cart to customer
            cart.customer = customer
            cart.save()
        else:
            # Try to find customer's existing cart or create new one
            cart = Cart.objects.filter(customer=customer, status='OPEN').first()
            if not cart:
                cart = Cart.objects.create(session_key=session_key, customer=customer, status='OPEN')
    elif not cart:
        # Create new cart for anonymous user
        cart = Cart.objects.create(session_key=session_key, status='OPEN')
    
    return cart


def add_item(cart: Cart, item_id: int, quantity: int = 1):
    item = get_object_or_404(Item, pk=item_id, is_active=True)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        item=item,
        defaults={'quantity': 0, 'unit_price': item.price}
    )
    cart_item.quantity += max(1, quantity)
    # snapshot unit price
    cart_item.unit_price = item.price
    cart_item.save()
    return cart_item


def set_quantity(cart: Cart, item_id: int, quantity: int):
    item = get_object_or_404(Item, pk=item_id)
    try:
        ci = CartItem.objects.get(cart=cart, item=item)
    except CartItem.DoesNotExist:
        return None
    if quantity <= 0:
        ci.delete()
        return None
    ci.quantity = quantity
    ci.save()
    return ci


def get_session_wishlist_ids(request):
    key = 'wishlist_item_ids'
    if key not in request.session:
        request.session[key] = []
    return request.session[key]
