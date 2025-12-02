from .utils import get_or_create_cart

def cart_context(request):
    try:
        cart = get_or_create_cart(request)
        count = sum(ci.quantity for ci in cart.items.all())
        total = sum(ci.subtotal for ci in cart.items.all())
    except Exception:
        count = 0
        total = 0
    return {
        'cart_count': count,
        'cart_total': total,
    }
