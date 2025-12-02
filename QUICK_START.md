# 🚀 Quick Start Guide - Order Workflow System

## ⚡ Setup (Already Done!)

All database migrations, item seeding, and user creation are complete. Your system is ready to test!

---

## 👥 Login Credentials

| Role | URL | Username | Password |
|------|-----|----------|----------|
| **Manager** | http://127.0.0.1:8000/manager/ | `manager` | `manager123` |
| **Chef** | http://127.0.0.1:8000/chef/ | `chef` | `chef123` |
| **Waiter** | http://127.0.0.1:8000/waiter/ | `waiter` | `waiter123` |
| **Customer** | http://127.0.0.1:8000/items/ | (any customer) | (any) |

---

## 🧪 Complete Workflow Test

### Step 1: Place Order (as Customer)

1. Start server: `python3 manage.py runserver`
2. Go to http://127.0.0.1:8000/items/
3. Add items to cart (try items from different categories!)
4. Click "Cart" → "Proceed to Checkout"
5. Choose **Dining** and enter:
   - Name: Test Customer
   - Phone: 9876543210
   - Table: 5
6. Click "Continue to payment"
7. Enter payment reference: `TEST123`
8. Click "Submit Payment"
9. **Note the Order ID** from the pending page

### Step 2: Verify Payment (as Manager)

1. **Logout** current session
2. Go to http://127.0.0.1:8000/manager/
3. Login: `manager` / `manager123`
4. Click "Payments" in navbar or go to `/manager/payments/`
5. Find your order in pending payments
6. Click **"Verify"** button
7. On confirmation page, click **"Send to Chef"**
8. ✅ Order is now sent to chef!

### Step 3: Prepare Order (as Chef)

1. **Logout** manager
2. Go to http://127.0.0.1:8000/chef/
3. Login: `chef` / `chef123`
4. See your order in "📋 Pending Orders" (FIFO queue)
5. Click **"🚀 Start Preparing"**
6. Order moves to "🍳 Preparing" section
7. Click **"✅ Mark as Ready"**
8. ✅ Order sent to waiter!

### Step 4: Deliver Order (as Waiter)

1. **Logout** chef
2. Go to http://127.0.0.1:8000/waiter/
3. Login: `waiter` / `waiter123`
4. See order in "✅ Ready for Pickup" → "🍽️ Dining Orders"
5. Note: Shows **Table 5** prominently
6. Click **"📤 Pick Up & Serve"**
7. Order moves to "🚀 Out for Delivery" section
8. Click **"✔️ Mark as Delivered"**
9. ✅ Order completed!

### Step 5: Verify Completion

1. Go to http://127.0.0.1:8000/my-orders/
2. Find your order
3. Status should show: **"Completed"** ✅

---

## 🧪 Test Different Scenarios

### Test 1: Delivery Order

Same as above but:
- Step 1: Choose **Delivery** instead of Dining
- Enter full address details
- Waiter will see address and phone number

### Test 2: Abandon and Restore

**Manager flow**:
1. After verifying payment, click **"🗑️ Abandon Order"**
2. Go to `/manager/orders/history/`
3. Filter by "Canceled"
4. Click **"↩️ Restore"** button
5. Order is back in chef's queue!

### Test 3: Reject Payment

**Manager flow**:
1. In payments page, click **"Reject"** instead of verify
2. Check order history - status is "Rejected"
3. Customer sees rejected status

### Test 4: Multiple Orders (FIFO)

1. Create 3 orders as customer
2. Manager verifies all 3, sends to chef
3. Chef sees all 3 in **exact order they were created**
4. FIFO = First In, First Out! ✅

---

## 🎨 UI Features to Notice

### Chef Dashboard:
- **Orange** borders for pending orders
- **Blue** borders for preparing orders
- Shows table numbers prominently
- Auto-refreshes every 30 seconds

### Waiter Dashboard:
- **Green** section for ready orders
- **Purple** section for out for delivery
- Dining vs Delivery clearly separated
- Shows table numbers OR full address
- Auto-refreshes every 20 seconds

### Manager:
- Color-coded status badges
- Filter orders by status
- Complete order history
- Payment status tracking

---

## 📦 Available Items (24 items total)

### Beverages (₹40-130):
- Filter Coffee, Cappuccino, Cold Coffee
- Masala Chai, Mocktails, Mojitos

### Snacks (₹30-180):
- Samosa, Spring Rolls, Paneer Tikka
- French Fries, Manchurian, Chilli Paneer

### Rice (₹90-250):
- Biryani varieties, Fried Rice
- Jeera Rice, Pulao, Curd Rice

---

## 🔍 Monitor Order Status

### Customer View:
- Go to "My Orders" in navbar
- See real-time status updates
- Track from pending to completed

### Manager View:
- Dashboard shows all statistics
- Order history has complete details
- Can filter by any status

---

## 🐛 Troubleshooting

### Can't login as chef/waiter?
```bash
python3 create_staff_users.py
```

### No items showing?
```bash
python3 seed_items.py
```

### Database issues?
```bash
python3 manage.py migrate
```

### Start fresh?
```bash
# Delete database
rm db.sqlite3
# Recreate
python3 manage.py migrate
python3 seed_items.py
python3 create_staff_users.py
```

---

## ✅ What to Look For

### ✅ Successful Flow:
1. Customer places order → Status: PENDING_PAYMENT
2. Manager verifies → Status: PAID → Sends to chef
3. Chef starts → Status: PREPARING
4. Chef marks ready → Status: READY_FOR_DELIVERY
5. Waiter picks up → Status: OUT_FOR_DELIVERY
6. Waiter delivers → Status: COMPLETED ✅

### ✅ All timestamps should be recorded:
- `created_at` - Order creation
- `sent_to_chef_at` - Manager sends to chef
- `preparing_started_at` - Chef starts
- `ready_at` - Chef marks ready
- `completed_at` - Waiter delivers

### ✅ Status updates visible everywhere:
- Customer "My Orders" page
- Manager dashboard
- Manager order history
- Real-time updates in chef/waiter dashboards

---

## 🎯 Key Features Demonstrated

1. ✅ **FIFO Queue**: Orders processed in order
2. ✅ **Role Separation**: Each role has specific dashboard
3. ✅ **Real-time Updates**: Auto-refresh keeps everyone informed
4. ✅ **Complete Traceability**: Timestamps at every stage
5. ✅ **Undo Capability**: Restore abandoned orders
6. ✅ **Professional UI**: Consistent design, color coding
7. ✅ **Item Categories**: Organized menu with 24 items

---

## 📞 Quick Commands

```bash
# Start server
python3 manage.py runserver

# Check system
python3 manage.py check

# Recreate staff users
python3 create_staff_users.py

# Reseed items
python3 seed_items.py
```

---

**Ready to Test!** 🚀

Open http://127.0.0.1:8000/ and follow the workflow above!
