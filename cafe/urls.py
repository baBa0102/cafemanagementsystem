from django.urls import path
from . import views

urlpatterns = [
    # Root to landing page
    path('', views.landing_page_view, name='homepage_view'),

    # AI Bot page
    path('ask-ai/', views.ai_bot_view, name='ai_bot'),
    path('api/ai/chat', views.ai_chat_api, name='ai_chat_api'),

    # Items and management
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/payments/', views.manager_payments_view, name='manager_payments'),
    path('manager/payment/<int:payment_id>/verify/', views.verify_payment, name='verify_payment'),
    path('manager/order/<int:order_id>/send-to-chef/', views.manager_send_to_chef_confirm, name='manager_send_to_chef_confirm'),
    path('manager/orders/history/', views.manager_order_history, name='manager_order_history'),
    path('manager/order/<int:order_id>/restore/', views.manager_restore_order, name='manager_restore_order'),
    path('manager/analytics/sales/', views.manager_sales_analytics, name='manager_sales'),
    path('manager/analytics/items/', views.manager_items_analytics, name='manager_items'),
    path('manager/analytics/customers/', views.manager_customers_analytics, name='manager_customers'),

    path('items/', views.items_list, name='items_list'),
    path('items/add/', views.item_create, name='item_create'),
    path('items/<int:pk>/edit/', views.item_update, name='item_update'),
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),

    # Cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),

    # Checkout
    path('checkout/', views.checkout_choose, name='checkout_choose'),
    path('checkout/dining/', views.checkout_dining, name='checkout_dining'),
    path('checkout/delivery/', views.checkout_delivery, name='checkout_delivery'),
    path('payment/', views.payment_page, name='payment_page'),
    path('order/<int:order_id>/status/', views.order_status, name='order_status'),
    path('order/<int:order_id>/status.json', views.order_status_json, name='order_status_json'),
    path('order/<int:order_id>/confirm/', views.order_confirm, name='order_confirm'),
    path('confirmation/', views.order_confirmation, name='order_confirmation'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('login/staff/', views.login_staff_view, name='login_staff'),
    path('logout/', views.logout_view, name='logout'),
    path('account/set-password/', views.set_password_view, name='set_password'),

    # Existing pages
    path('mealkits/', views.meal_kits_view, name='meal_kits'),
    path('landing/', views.landing_page_view, name='landing_page'),
    path('contact/', views.contact_page_view, name='contact_page'),

    # Account and wishlist
    path('account/', views.my_account_view, name='my_account'),
    path('wishlist/add/<int:item_id>/', views.wishlist_add, name='wishlist_add'),
    path('wishlist/remove/<int:item_id>/', views.wishlist_remove, name='wishlist_remove'),
    
    # Orders tracking
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('track-order/', views.track_order_view, name='track_order'),
    path('track-order/<int:order_id>/', views.track_order_view, name='track_order_detail'),
    
    # Chef dashboard
    path('chef/', views.chef_dashboard, name='chef_dashboard'),
    path('chef/order/<int:order_id>/start/', views.chef_start_preparing, name='chef_start_preparing'),
    path('chef/order/<int:order_id>/ready/', views.chef_mark_ready, name='chef_mark_ready'),
    
    # Waiter/Transit dashboard
    path('waiter/', views.waiter_dashboard, name='waiter_dashboard'),
    path('waiter/order/<int:order_id>/pickup/', views.waiter_pickup_order, name='waiter_pickup_order'),
    path('waiter/order/<int:order_id>/complete/', views.waiter_complete_order, name='waiter_complete_order'),
]
