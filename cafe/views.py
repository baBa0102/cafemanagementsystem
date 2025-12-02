# cafe/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.db import models
from .models import Item, CartItem, Order, OrderItem, Customer, Address, Offer, WishlistItem, Payment
from .forms import ItemForm, DiningForm, DeliveryForm
from .utils import get_or_create_cart, add_item, set_quantity, get_session_wishlist_ids
from .ai_engine import CafeAIEngine
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import logging

logger = logging.getLogger(__name__)

# 1. View for the main HomePage (Accesses the project-level template)
def homepage_view(request):
    return render(request, 'cafemanagementsystem/HomePage.html')

# 2. View for the new Meal Kits Page
def meal_kits_view(request):
    """Renders the CITY Meal Kits landing page."""
    return render(request, 'cafe/meal_kits.html')

# View for landing page
def landing_page_view(request):
    """Renders the combined scrolling landing page."""
    return render(request, 'cafe/landing_page.html')

# view for contact page
def contact_page_view(request):
    """Renders the contact page."""
    return render(request, 'cafe/contact.html')

# AI Bot page (UI shell, integration to be added later)
@ensure_csrf_cookie
def ai_bot_view(request):
    # Reset AI state on page load/refresh so each visit starts clean
    request.session['ai_state'] = {
        'items': [],
        'order_type': None,
        'details': {},
        'awaiting_fields': [],
        'summary_confirmed': False,
    }
    request.session.pop('chat_history', None)
    request.session.pop('ai_conversation_history', None)
    return render(request, 'cafe/ai_bot.html')


@require_POST
def ai_chat_api(request):
    """Handle AI assistant requests entirely within our system."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    message = (payload.get('message') or '').strip()
    if not message:
        return JsonResponse({"error": "Missing 'message'."}, status=400)

    engine = CafeAIEngine(request)
    try:
        response = engine.handle(message)
        engine.persist()
    except Exception as exc:  # pragma: no cover - unexpected failure path
        logger.exception("AI assistant failed to handle message", exc_info=exc)
        return JsonResponse({"error": "AI assistant is unavailable right now. Please try again."}, status=500)

    return JsonResponse(response)

# ---- Manager permission helper ----
def is_manager(user):
    return user.is_authenticated and (user.is_staff or user.groups.filter(name='Manager').exists())


# ---- Items: list and CRUD ----
def items_list(request):
    items = Item.objects.filter(is_active=True)
    return render(request, 'cafe/items_list.html', {"items": items})


@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    # Aggregations for analytics
    from django.db.models import Sum, Count, Avg, F
    from django.db.models.functions import ExtractHour, TruncDate
    from decimal import Decimal
    
    # Top items by quantity
    top_items = (
        OrderItem.objects
        .values('item__name', 'item_id')
        .annotate(total_qty=Sum('quantity'), total_revenue=Sum(F('quantity') * F('unit_price')))
        .order_by('-total_qty')[:10]
    )
    
    # Orders by hour
    orders_by_hour = (
        Order.objects
        .annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(c=Count('id'))
        .order_by('hour')
    )
    
    # Daily revenue trend (last 7 days)
    from datetime import timedelta
    from django.utils import timezone
    week_ago = timezone.now() - timedelta(days=7)
    daily_revenue = (
        Order.objects
        .filter(created_at__gte=week_ago, status__in=['PAID', 'PREPARING', 'COMPLETED'])
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('date')
    )
    
    # Order statistics
    total_orders = Order.objects.count()
    status_counts = Order.objects.values('status').annotate(c=Count('id'))
    
    # Revenue metrics
    total_revenue = Order.objects.filter(status__in=['PAID', 'PREPARING', 'COMPLETED']).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    avg_order_value = Order.objects.filter(status__in=['PAID', 'PREPARING', 'COMPLETED']).aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0')
    
    # Pending payments
    payments_pending = Payment.objects.filter(status='PENDING').select_related('order', 'order__customer').order_by('-created_at')[:20]
    
    # Recent customers
    customers = Customer.objects.annotate(
        order_count=Count('orders')
    ).order_by('-created_at')[:10]
    
    # Order type distribution
    order_type_dist = Order.objects.values('order_type').annotate(c=Count('id'))
    
    # Calculate percentage for status distribution
    status_percentages = []
    for sc in status_counts:
        percentage = (sc['c'] / total_orders * 100) if total_orders > 0 else 0
        status_percentages.append({'status': sc['status'], 'count': sc['c'], 'percentage': round(percentage, 1)})
    
    context = {
        'top_items': list(top_items),
        'orders_by_hour': list(orders_by_hour),
        'daily_revenue': list(daily_revenue),
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'status_counts': list(status_counts),
        'status_percentages': status_percentages,
        'order_type_dist': list(order_type_dist),
        'payments_pending': payments_pending,
        'customers': customers,
    }
    return render(request, 'cafe/manager_dashboard.html', context)



@login_required
@user_passes_test(is_manager)

def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item created')
            return redirect('items_list')
    else:
        form = ItemForm()
    return render(request, 'cafe/item_form.html', {"form": form, "title": "Add Item"})



@login_required
@user_passes_test(is_manager)

def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated')
            return redirect('items_list')
    else:
        form = ItemForm(instance=item)
    return render(request, 'cafe/item_form.html', {"form": form, "title": "Edit Item"})



@login_required
@user_passes_test(is_manager)

def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted')
        return redirect('items_list')
    return render(request, 'cafe/item_confirm_delete.html', {"item": item})


# ---- Cart ----

def cart_detail(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related('item')
    total = sum(ci.subtotal for ci in items)
    return render(request, 'cafe/cart.html', {"cart": cart, "items": items, "total": total})



def add_to_cart(request, item_id):
    cart = get_or_create_cart(request)
    add_item(cart, item_id, quantity=1)
    messages.success(request, 'Added to cart')
    # Redirect back with a flag to trigger the dining/delivery prompt
    referer = request.META.get('HTTP_REFERER', reverse('items_list'))
    sep = '&' if '?' in referer else '?'
    return redirect(f"{referer}{sep}added=1")



def update_cart(request, item_id):
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', '1'))
        cart = get_or_create_cart(request)
        set_quantity(cart, item_id, qty)
        messages.success(request, 'Cart updated')
    return redirect('cart_detail')


# ---- Checkout ----

def checkout_choose(request):
    return render(request, 'cafe/checkout_choose.html')



def _ensure_customer_user_and_login(request, customer: Customer, cart=None):
    User = get_user_model()
    # Remember current session key tied to the cart
    old_session_key = request.session.session_key
    user_just_created = False
    
    if not customer.user:
        # Set username as phone number; ensure uniqueness by suffixing if needed
        base = (customer.phone or '').strip().replace(' ', '')
        if not base:
            # Fallback to sanitized name if phone missing
            base = (customer.name or 'guest').strip().replace(' ', '').lower()
        username = base
        i = 1
        while User.objects.filter(username=username).exists():
            i += 1
            username = f"{base}{i}"
        user = User.objects.create(username=username)
        # attach email if available
        if customer.email:
            user.email = customer.email
        user.set_unusable_password()
        user.save()
        customer.user = user
        customer.save()
        user_just_created = True
    
    login(request, customer.user)
    # Ensure a session key exists post-login and move cart to new session key
    if not request.session.session_key:
        request.session.save()
    new_session_key = request.session.session_key
    if cart is not None and new_session_key and cart.session_key != new_session_key:
        cart.session_key = new_session_key
        cart.save()
    
    # Only set flag if user was just created AND doesn't have a password yet
    if user_just_created and not customer.user.has_usable_password():
        request.session['account_created_username'] = customer.user.username



def checkout_dining(request):
    cart = get_or_create_cart(request)
    
    # Check if user is logged in and has a customer profile
    existing_customer = None
    edit_mode = request.GET.get('edit') == '1'
    
    if request.user.is_authenticated:
        try:
            existing_customer = request.user.customer_profile
        except Customer.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = DiningForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            table_no = form.cleaned_data['table_no']
            customer, _ = Customer.objects.get_or_create(name=name, phone=phone)
            cart.customer = customer
            cart.save()
            
            # Only do login flow if user is not already authenticated with a password
            if not (request.user.is_authenticated and request.user.has_usable_password()):
                _ensure_customer_user_and_login(request, customer, cart)
            
            request.session['order_type'] = 'DINING'
            request.session['table_no'] = table_no
            return redirect('payment_page')
    else:
        # Pre-fill form for existing customers
        initial = {}
        if existing_customer and not edit_mode:
            initial = {
                'name': existing_customer.name,
                'phone': existing_customer.phone,
            }
        form = DiningForm(initial=initial)
    
    return render(request, 'cafe/checkout_dining.html', {
        "form": form,
        "existing_customer": existing_customer,
        "edit_mode": edit_mode
    })



def checkout_delivery(request):
    cart = get_or_create_cart(request)
    
    # Check if user is logged in and has a customer profile
    existing_customer = None
    default_address = None
    edit_mode = request.GET.get('edit') == '1'
    
    if request.user.is_authenticated:
        try:
            existing_customer = request.user.customer_profile
            default_address = existing_customer.addresses.filter(is_default=True).first()
        except Customer.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = DeliveryForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            email = form.cleaned_data.get('email')
            customer, _ = Customer.objects.get_or_create(name=name, phone=phone, defaults={'email': email})
            if email and not customer.email:
                customer.email = email
                customer.save()
            addr = Address.objects.create(
                customer=customer,
                line1=form.cleaned_data['line1'],
                line2=form.cleaned_data.get('line2', ''),
                city=form.cleaned_data['city'],
                state=form.cleaned_data.get('state', ''),
                postal_code=form.cleaned_data.get('postal_code', ''),
                is_default=form.cleaned_data.get('make_default', True)
            )
            if addr.is_default:
                # make others non-default
                Address.objects.filter(customer=customer).exclude(id=addr.id).update(is_default=False)
            cart.customer = customer
            cart.save()
            
            # Only do login flow if user is not already authenticated with a password
            if not (request.user.is_authenticated and request.user.has_usable_password()):
                _ensure_customer_user_and_login(request, customer, cart)
            
            request.session['order_type'] = 'DELIVERY'
            request.session['delivery_address_id'] = addr.id
            return redirect('payment_page')
    else:
        # Pre-fill form for existing customers with default address
        initial = {}
        if existing_customer and not edit_mode:
            initial = {
                'name': existing_customer.name,
                'phone': existing_customer.phone,
                'email': existing_customer.email or '',
            }
            if default_address:
                initial.update({
                    'line1': default_address.line1,
                    'line2': default_address.line2,
                    'city': default_address.city,
                    'state': default_address.state,
                    'postal_code': default_address.postal_code,
                })
        form = DeliveryForm(initial=initial)
    
    return render(request, 'cafe/checkout_delivery.html', {
        "form": form,
        "existing_customer": existing_customer,
        "default_address": default_address,
        "edit_mode": edit_mode
    })



def payment_page(request):
    from .models import PaymentConfig, Payment  # local import to avoid circular
    cart = get_or_create_cart(request)
    paycfg = PaymentConfig.objects.first()
    account_created_username = request.session.pop('account_created_username', None)
    if request.method == 'POST':
        # Backend-driven payment submission and verification (no instant success)
        order_type = request.session.get('order_type')
        if not order_type:
            messages.error(request, 'Choose checkout type first')
            return redirect('checkout_choose')
        customer = cart.customer
        if not customer:
            messages.error(request, 'Customer details missing')
            return redirect('checkout_choose')
        address = None
        table_no = ''
        if order_type == 'DELIVERY':
            addr_id = request.session.get('delivery_address_id')
            address = Address.objects.filter(id=addr_id, customer=customer).first()
        else:
            table_no = request.session.get('table_no', '')

        items = list(cart.items.select_related('item'))
        total = sum(ci.subtotal for ci in items)
        # Create order in PENDING_PAYMENT and record a Payment awaiting verification
        order = Order.objects.create(
            customer=customer,
            order_type=order_type,
            table_no=table_no,
            delivery_address=address,
            total_amount=total,
            status='PENDING_PAYMENT',
        )
        for ci in items:
            OrderItem.objects.create(order=order, item=ci.item, quantity=ci.quantity, unit_price=ci.unit_price)
        # Clear cart
        cart.items.all().delete()
        cart.status = 'CHECKED_OUT'
        cart.save()
        # Save payment reference from user input (optional)
        reference = request.POST.get('reference', '').strip()
        Payment.objects.create(order=order, amount=total, reference=reference, status='PENDING')
        return redirect('order_status', order_id=order.id)

    return render(request, 'cafe/payment.html', {"paycfg": paycfg, "cart": cart, "account_created_username": account_created_username})



def order_confirmation(request):
    order_type = request.session.get('last_order_type', 'DINING')
    return render(request, 'cafe/confirmation.html', {"order_type": order_type})




@login_required
@user_passes_test(is_manager)

def manager_sales_analytics(request):
    """Detailed sales analytics page."""
    from django.db.models import Sum, Count, Avg, F
    from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
    from datetime import timedelta
    from django.utils import timezone
    from decimal import Decimal
    
    # Date range filter
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Daily revenue
    daily_revenue = (
        Order.objects
        .filter(created_at__gte=start_date, status__in=['PAID', 'PREPARING', 'COMPLETED'])
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('date')
    )
    
    # Total metrics
    total_revenue = Order.objects.filter(
        created_at__gte=start_date, 
        status__in=['PAID', 'PREPARING', 'COMPLETED']
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    
    total_orders = Order.objects.filter(created_at__gte=start_date).count()
    avg_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')
    
    # Order type breakdown
    order_type_revenue = Order.objects.filter(
        created_at__gte=start_date,
        status__in=['PAID', 'PREPARING', 'COMPLETED']
    ).values('order_type').annotate(
        revenue=Sum('total_amount'),
        count=Count('id')
    )
    
    context = {
        'daily_revenue': list(daily_revenue),
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'order_type_revenue': list(order_type_revenue),
        'days': days,
    }
    return render(request, 'cafe/manager_sales.html', context)



@login_required
@user_passes_test(is_manager)

def manager_items_analytics(request):
    """Detailed items performance analytics."""
    from django.db.models import Sum, Count, F, Avg
    from datetime import timedelta
    from django.utils import timezone
    
    # Date range filter
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Most popular items
    top_items = (
        OrderItem.objects
        .filter(order__created_at__gte=start_date, order__status__in=['PAID', 'PREPARING', 'COMPLETED'])
        .values('item__name', 'item__id', 'item__price')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('unit_price')),
            order_count=Count('order', distinct=True)
        )
        .order_by('-total_qty')
    )
    
    # Items that need restocking attention (low performers)
    low_performers = (
        OrderItem.objects
        .filter(order__created_at__gte=start_date, order__status__in=['PAID', 'PREPARING', 'COMPLETED'])
        .values('item__name', 'item__id')
        .annotate(total_qty=Sum('quantity'))
        .order_by('total_qty')[:10]
    )
    
    context = {
        'top_items': list(top_items),
        'low_performers': list(low_performers),
        'days': days,
    }
    return render(request, 'cafe/manager_items.html', context)



@login_required
@user_passes_test(is_manager)

def manager_customers_analytics(request):
    """Detailed customer analytics."""
    from django.db.models import Sum, Count, Avg
    from datetime import timedelta
    from django.utils import timezone
    
    # Top customers by spending
    top_customers = (
        Customer.objects
        .annotate(
            spent_amount=Sum('orders__total_amount', filter=models.Q(orders__status__in=['PAID', 'PREPARING', 'COMPLETED'])),
            order_count=Count('orders')
        )
        .filter(spent_amount__isnull=False)
        .order_by('-spent_amount')[:20]
    )
    
    # Customer acquisition trend
    days = 30
    start_date = timezone.now() - timedelta(days=days)
    new_customers = Customer.objects.filter(created_at__gte=start_date).count()
    total_customers = Customer.objects.count()
    
    # Average customer metrics
    avg_customer_value = Customer.objects.aggregate(
        avg_spent=Avg('orders__total_amount', filter=models.Q(orders__status__in=['PAID', 'PREPARING', 'COMPLETED']))
    )['avg_spent'] or 0
    
    context = {
        'top_customers': list(top_customers),
        'new_customers': new_customers,
        'total_customers': total_customers,
        'avg_customer_value': avg_customer_value,
        'days': days,
    }
    return render(request, 'cafe/manager_customers.html', context)



@login_required
@user_passes_test(is_manager)

def manager_payments_view(request):
    """Dedicated payment verification page for managers"""
    from django.db.models import Sum
    from datetime import timedelta
    from django.utils import timezone
    
    # Get all pending payments
    payments_pending = Payment.objects.filter(status='PENDING').select_related('order', 'order__customer', 'order__delivery_address').prefetch_related('order__items__item').order_by('-created_at')
    
    # Get verified payments today
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    verified_today = Payment.objects.filter(status='VERIFIED', verified_at__gte=today_start).count()
    
    # Calculate total pending amount
    total_pending = payments_pending.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'payments_pending': payments_pending,
        'verified_today': verified_today,
        'total_pending': total_pending,
    }
    return render(request, 'cafe/manager_payments.html', context)



@login_required
@user_passes_test(is_manager)

def verify_payment(request, payment_id: int):
    """Manager/Admin can verify a payment."""
    from .models import Payment
    from django.utils import timezone
    
    payment = get_object_or_404(Payment, pk=payment_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            payment.status = 'VERIFIED'
            payment.verified_at = timezone.now()
            payment.save()
            # Update order status to PAID
            payment.order.status = 'PAID'
            payment.order.save()
            messages.success(request, f'Payment for Order #{payment.order.id} verified.')
            # Store order ID in session for next step
            request.session['verified_order_id'] = payment.order.id
            return redirect('manager_send_to_chef_confirm', order_id=payment.order.id)
        elif action == 'reject':
            payment.status = 'FAILED'
            payment.save()
            payment.order.status = 'REJECTED'
            payment.order.save()
            messages.warning(request, f'Payment for Order #{payment.order.id} rejected.')
    # Check where to redirect - if from dedicated payments page, go back there
    referer = request.META.get('HTTP_REFERER', '')
    if 'payments' in referer:
        return redirect('manager_payments')
    return redirect('manager_dashboard')



@login_required
@user_passes_test(is_manager)

def manager_send_to_chef_confirm(request, order_id):
    """Confirmation page to send order to chef or abandon"""
    from django.utils import timezone
    
    order = get_object_or_404(Order, pk=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'send_to_chef':
            order.sent_to_chef_at = timezone.now()
            order.save()
            messages.success(request, f'Order #{order_id} sent to chef for preparation!')
            return redirect('manager_payments')
        elif action == 'abandon':
            # Move to canceled but keep in history
            order.status = 'CANCELED'
            order.save()
            messages.info(request, f'Order #{order_id} abandoned. You can restore it from order history.')
            return redirect('manager_order_history')
    
    # Show order details for confirmation
    order_items = order.items.all().select_related('item')
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'cafe/manager_send_to_chef.html', context)



@login_required
@user_passes_test(is_manager)

def manager_order_history(request):
    """View all orders including canceled ones with option to restore"""
    from django.db.models import Q
    
    # Get status filter from query params
    status_filter = request.GET.get('status', 'all')
    
    orders = Order.objects.all().select_related('customer', 'payment').prefetch_related('items__item').order_by('-created_at')
    
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'cafe/manager_order_history.html', context)



@login_required
@user_passes_test(is_manager)

def manager_restore_order(request, order_id):
    """Restore a canceled order and send to chef"""
    from django.utils import timezone
    
    order = get_object_or_404(Order, pk=order_id)
    if request.method == 'POST' and order.status == 'CANCELED':
        # Restore order to PAID status
        order.status = 'PAID'
        order.sent_to_chef_at = timezone.now()
        order.save()
        messages.success(request, f'Order #{order_id} restored and sent to chef!')
        return redirect('manager_order_history')
    return redirect('manager_order_history')



def order_status(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    # If paid, show confirmation; else show waiting page
    if order.status == 'PAID':
        request.session['last_order_type'] = order.order_type
        return render(request, 'cafe/confirmation.html', {"order_type": order.order_type, "order": order})
    return render(request, 'cafe/order_pending.html', {"order": order})



def order_status_json(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    return JsonResponse({"status": order.status})



def order_confirm(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    request.session['last_order_type'] = order.order_type
    return render(request, 'cafe/confirmation.html', {"order_type": order.order_type, "order": order})



def my_account_view(request):
    cart = get_or_create_cart(request)
    customer = cart.customer
    offers = Offer.objects.filter(active=True)
    session_wishlist_ids = get_session_wishlist_ids(request)
    wishlist_items = []
    if customer:
        wishlist_items = list(WishlistItem.objects.filter(customer=customer).select_related('item'))
    context = {
        'customer': customer,
        'orders': customer.orders.all().prefetch_related('items', 'payment').order_by('-created_at') if customer else [],
        'addresses': customer.addresses.all() if customer else [],
        'offers': offers,
        'session_wishlist_ids': session_wishlist_ids,
        'wishlist_items': wishlist_items,
    }
    return render(request, 'cafe/account.html', context)



def my_orders_view(request):
    """View for users to see their orders - both logged in and guest orders"""
    cart = get_or_create_cart(request)
    customer = cart.customer
    
    # Get orders for logged-in customer
    orders = []
    if customer:
        orders = customer.orders.all().prefetch_related('items__item', 'payment').order_by('-created_at')
    
    context = {
        'customer': customer,
        'orders': orders,
    }
    return render(request, 'cafe/my_orders.html', context)



def track_order_view(request, order_id=None):
    """Track a specific order by ID - accessible to anyone with the order ID"""
    if order_id:
        order = get_object_or_404(Order, pk=order_id)
    else:
        # Allow tracking by order ID from form
        order_id = request.GET.get('order_id') or request.POST.get('order_id')
        if not order_id:
            return render(request, 'cafe/track_order.html', {'order': None})
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            messages.error(request, f'Order #{order_id} not found')
            return render(request, 'cafe/track_order.html', {'order': None, 'not_found': True})
    
    # Get order items and payment info
    order_items = order.items.all().select_related('item')
    try:
        payment = order.payment
    except:
        payment = None
    
    context = {
        'order': order,
        'order_items': order_items,
        'payment': payment,
    }
    return render(request, 'cafe/track_order.html', context)



def wishlist_add(request, item_id):
    cart = get_or_create_cart(request)
    customer = cart.customer
    if customer:
        WishlistItem.objects.get_or_create(customer=customer, item_id=item_id)
        messages.success(request, 'Added to wishlist')
    else:
        ids = get_session_wishlist_ids(request)
        if item_id not in ids:
            ids.append(item_id)
            request.session.modified = True
        messages.success(request, 'Saved to wishlist for this session')
    return redirect(request.META.get('HTTP_REFERER', reverse('items_list')))



def wishlist_remove(request, item_id):
    cart = get_or_create_cart(request)
    customer = cart.customer
    if customer:
        WishlistItem.objects.filter(customer=customer, item_id=item_id).delete()
        messages.success(request, 'Removed from wishlist')
    else:
        ids = get_session_wishlist_ids(request)
        if item_id in ids:
            ids.remove(item_id)
            request.session.modified = True
        messages.success(request, 'Removed from session wishlist')
    return redirect(request.META.get('HTTP_REFERER', reverse('my_account')))


# ---- Auth (User and Staff/Manager) ----


def login_view(request, mode='user'):
    """
    mode: 'user' (default) or 'staff'. Staff mode allows Manager, Chef, Waiter.
    """
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        # Check if user has staff access (Manager, Chef, or Waiter)
        is_manager = user.is_staff or user.groups.filter(name='Manager').exists()
        is_chef = user.groups.filter(name='Chef').exists()
        is_waiter = user.groups.filter(name='Waiter').exists()
        has_staff_access = is_manager or is_chef or is_waiter
        
        if mode == 'staff' and not has_staff_access:
            messages.error(request, 'Staff access only (Manager/Chef/Waiter).')
        else:
            login(request, user)
            nxt = request.GET.get('next') or request.POST.get('next')
            if nxt:
                return redirect(nxt)
            # Redirect based on role
            if is_chef:
                return redirect('chef_dashboard')
            elif is_waiter:
                return redirect('waiter_dashboard')
            elif is_manager:
                return redirect('manager_dashboard')
            return redirect('items_list')
    context = {"form": form, "mode": mode}
    return render(request, 'cafe/login.html', context)



def login_staff_view(request):
    return login_view(request, mode='staff')



def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('homepage_view')



@login_required

def set_password_view(request):
    # Preserve cart before password change
    cart = get_or_create_cart(request)
    old_session_key = request.session.session_key
    
    form = SetPasswordForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        # Re-login user after password change
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, form.user)
        
        # Ensure cart is preserved with current session
        if old_session_key and request.session.session_key:
            cart.session_key = request.session.session_key
            cart.save()
        
        messages.success(request, 'Password has been set.')
        return redirect('my_account')
    return render(request, 'cafe/set_password.html', {"form": form})


# ---- Helper functions for Chef and Waiter roles ----

def is_chef(user):
    return user.is_authenticated and (user.groups.filter(name='Chef').exists() or user.is_staff)



def is_waiter(user):
    return user.is_authenticated and (user.groups.filter(name='Waiter').exists() or user.is_staff)


# ---- Chef Dashboard ----

@login_required
@user_passes_test(is_chef)

def chef_dashboard(request):
    """Chef dashboard showing orders pending preparation in FIFO order"""
    from django.utils import timezone
    
    # Orders sent to chef but not yet being prepared (PAID status)
    pending_orders = Order.objects.filter(
        status='PAID'
    ).select_related('customer', 'delivery_address').prefetch_related('items__item').order_by('sent_to_chef_at', 'created_at')
    
    # Orders currently being prepared
    preparing_orders = Order.objects.filter(
        status='PREPARING'
    ).select_related('customer', 'delivery_address').prefetch_related('items__item').order_by('preparing_started_at')
    
    context = {
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
    }
    return render(request, 'cafe/chef_dashboard.html', context)



@login_required
@user_passes_test(is_chef)

def chef_start_preparing(request, order_id):
    """Mark order as being prepared"""
    from django.utils import timezone
    
    order = get_object_or_404(Order, pk=order_id)
    if order.status == 'PAID':
        order.status = 'PREPARING'
        order.preparing_started_at = timezone.now()
        order.save()
        messages.success(request, f'Started preparing Order #{order_id}')
    else:
        messages.error(request, f'Order #{order_id} cannot be moved to preparing')
    
    return redirect('chef_dashboard')



@login_required
@user_passes_test(is_chef)

def chef_mark_ready(request, order_id):
    """Mark order as ready for delivery/pickup"""
    from django.utils import timezone
    
    order = get_object_or_404(Order, pk=order_id)
    if order.status == 'PREPARING':
        order.status = 'READY_FOR_DELIVERY'
        order.ready_at = timezone.now()
        order.save()
        messages.success(request, f'Order #{order_id} is ready for delivery!')
    else:
        messages.error(request, f'Order #{order_id} is not in preparing status')
    
    return redirect('chef_dashboard')


# ---- Waiter/Transit Dashboard ----

@login_required
@user_passes_test(is_waiter)

def waiter_dashboard(request):
    """Waiter dashboard showing orders ready for delivery"""
    
    # Orders ready for delivery/serving
    ready_orders = Order.objects.filter(
        status='READY_FOR_DELIVERY'
    ).select_related('customer', 'delivery_address').prefetch_related('items__item').order_by('ready_at')
    
    # Orders out for delivery
    out_orders = Order.objects.filter(
        status='OUT_FOR_DELIVERY'
    ).select_related('customer', 'delivery_address').prefetch_related('items__item').order_by('updated_at')
    
    # Separate dining and delivery
    dining_ready = [o for o in ready_orders if o.order_type == 'DINING']
    delivery_ready = [o for o in ready_orders if o.order_type == 'DELIVERY']
    
    dining_out = [o for o in out_orders if o.order_type == 'DINING']
    delivery_out = [o for o in out_orders if o.order_type == 'DELIVERY']
    
    context = {
        'dining_ready': dining_ready,
        'delivery_ready': delivery_ready,
        'dining_out': dining_out,
        'delivery_out': delivery_out,
    }
    return render(request, 'cafe/waiter_dashboard.html', context)



@login_required
@user_passes_test(is_waiter)

def waiter_pickup_order(request, order_id):
    """Mark order as picked up by waiter/delivery person"""
    from django.utils import timezone
    
    order = get_object_or_404(Order, pk=order_id)
    if order.status == 'READY_FOR_DELIVERY':
        order.status = 'OUT_FOR_DELIVERY'
        order.save()
        messages.success(request, f'Picked up Order #{order_id}')
    else:
        messages.error(request, f'Order #{order_id} is not ready for pickup')
    
    return redirect('waiter_dashboard')



@login_required
@user_passes_test(is_waiter)

def waiter_complete_order(request, order_id):
    """Mark order as delivered/completed"""
    from django.utils import timezone
    
    order = get_object_or_404(Order, pk=order_id)
    if order.status == 'OUT_FOR_DELIVERY':
        order.status = 'COMPLETED'
        order.completed_at = timezone.now()
        order.save()
        messages.success(request, f'Order #{order_id} completed!')
    else:
        messages.error(request, f'Order #{order_id} is not out for delivery')
    
    return redirect('waiter_dashboard')
