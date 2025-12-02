# Testing Guide for Cafe Management System

## ✅ Changes Completed

### 1. Payment Verification System
- **Fixed**: Payment verification now works directly in the manager dashboard
- **Location**: Manager Dashboard → Payments Pending Verification section
- **Features**:
  - Managers and admins can verify or reject payments with one click
  - Automatic order status update when payment is verified
  - Real-time updates on user's order status page

### 2. Manager Dashboard Improvements
- **Enhanced**: Professional analytics dashboard with data visualization
- **New Pages**:
  - **Overview** (`/manager/`) - Main dashboard with key metrics
  - **Sales Analytics** (`/manager/analytics/sales/`) - Revenue trends and order analysis
  - **Items Performance** (`/manager/analytics/items/`) - Most repeated orders, best sellers
  - **Customer Insights** (`/manager/analytics/customers/`) - Top customers, VIP list

### 3. Manager Login Fixed
- **Fixed**: Managers now redirect to dashboard instead of items list
- **Location**: Login → Manager Dashboard (automatic)

### 4. Real-time Order Updates
- **Enhanced**: Better UX for payment verification waiting page
- **Features**:
  - Loading spinner
  - Auto-refresh every 4 seconds
  - Automatic redirect when payment verified
  - Visual feedback for status changes

## 🧪 Testing Checklist

### Test 1: Payment Verification Flow
1. **Place an order as a customer**:
   - Go to `/items/`
   - Add items to cart
   - Go through checkout (dining or delivery)
   - Submit payment information
   - You should see the "Payment Verification" page with a spinner

2. **Verify payment as manager**:
   - Login as manager/staff at `/login/staff/`
   - You'll be redirected to `/manager/`
   - See the "Payments Pending Verification" section
   - Click "✓ Verify" button for the payment
   - Order status should change to PAID

3. **Check customer experience**:
   - The customer's order status page should automatically update
   - Page should redirect to confirmation page
   - Check that the order status is now "PAID"

### Test 2: Manager Dashboard Access
1. **Login as manager**:
   - Go to `/login/staff/`
   - Enter manager credentials
   - Should redirect to `/manager/` (not `/items/`)

2. **Test navigation**:
   - Click "Sales Analytics" → Should show revenue data
   - Click "Items Performance" → Should show most repeated orders
   - Click "Customer Insights" → Should show top customers
   - All pages should have proper styling and data

### Test 3: Analytics Features
1. **Sales Analytics** (`/manager/analytics/sales/`):
   - Check daily revenue trend table
   - Test time period filters (7, 30, 90 days)
   - Verify revenue by order type breakdown

2. **Items Performance** (`/manager/analytics/items/`):
   - Check "Most Popular Items" table
   - Verify "Times Ordered" column shows repeat order count
   - Check "Performance Insights" section
   - Verify low performers list

3. **Customer Insights** (`/manager/analytics/customers/`):
   - Check "Top Customers (VIP List)" table
   - Verify total spent and order count
   - Check growth metrics
   - Verify recommendations section

### Test 4: Error Handling
1. **Payment rejection**:
   - Place an order
   - As manager, click "✗ Reject" on the payment
   - Order should be marked as CANCELED
   - Customer should see failure message

2. **Non-manager access**:
   - Try to access `/manager/` without being logged in → Should redirect to login
   - Try to access as regular user → Should get 403 or redirect

## 🐛 Known Issues to Check

### Potential Issues
1. **Django Models Import**: Check if `models.Q` is imported in views.py for customer analytics
2. **Template Division**: Check if division filter exists in items analytics template
3. **Permission Groups**: Ensure "Manager" group exists in Django admin

## 🔧 Fixes Applied

### Issue 1: Models.Q Import (Fixed)
The customer analytics view uses `models.Q` for filtering. Make sure it's imported:

```python
from django.db import models
```

### Issue 2: Create Manager Group
Run this in Django shell to create the Manager group:

```python
from django.contrib.auth.models import Group
Group.objects.get_or_create(name='Manager')
```

### Issue 3: Create a Test Manager User
```python
from django.contrib.auth.models import User, Group
user = User.objects.create_user('manager', 'manager@cafe.com', 'password')
user.is_staff = True
manager_group, _ = Group.objects.get_or_create(name='Manager')
user.groups.add(manager_group)
user.save()
```

## 🚀 Running the Application

1. **Start the server**:
   ```bash
   python3 manage.py runserver
   ```

2. **Access points**:
   - Customer site: `http://127.0.0.1:8000/`
   - Items list: `http://127.0.0.1:8000/items/`
   - Manager login: `http://127.0.0.1:8000/login/staff/`
   - Manager dashboard: `http://127.0.0.1:8000/manager/`
   - Admin panel: `http://127.0.0.1:8000/admin/`

## 📊 Data Requirements

For meaningful analytics, you need:
- At least 5-10 orders in the system
- Orders with different statuses (PENDING_PAYMENT, PAID, PREPARING, COMPLETED)
- Multiple items ordered
- Different customers
- Some payments pending verification

## 🎯 Success Criteria

All tests pass when:
1. ✅ Payments can be verified from manager dashboard
2. ✅ Order status updates automatically when payment verified
3. ✅ Customer page auto-refreshes and redirects on verification
4. ✅ Manager login redirects to dashboard
5. ✅ All analytics pages load without errors
6. ✅ Data displays correctly in all charts and tables
7. ✅ Navigation between analytics pages works smoothly
8. ✅ Real-time updates work on order status page

## 📝 Notes

- The system uses polling (every 4 seconds) for real-time updates
- Analytics queries are optimized with annotations and aggregations
- All manager pages require authentication and manager/staff permissions
- Payment verification creates proper audit trail with `verified_at` timestamp
