# 🔐 Staff Login Guide - FIXED

## ✅ Issue Fixed

Chef and Waiter users can now login at `/login/staff/` and will be automatically redirected to their respective dashboards.

---

## 📋 Login Methods

### Method 1: Staff Login Page (Recommended)
**URL**: http://127.0.0.1:8000/login/staff/

This page accepts:
- ✅ Manager (redirects to `/manager/`)
- ✅ Chef (redirects to `/chef/`)
- ✅ Waiter (redirects to `/waiter/`)
- ❌ Regular customers (shows error)

### Method 2: Regular Login Page
**URL**: http://127.0.0.1:8000/login/

This page accepts all users and redirects based on role:
- Manager → `/manager/`
- Chef → `/chef/`
- Waiter → `/waiter/`
- Customer → `/items/`

### Method 3: Direct Dashboard Access
You can also go directly to the dashboard:
- http://127.0.0.1:8000/chef/ (login required)
- http://127.0.0.1:8000/waiter/ (login required)
- http://127.0.0.1:8000/manager/ (login required)

---

## 🧪 Test Each Staff User

### Test Chef Login:

1. Go to http://127.0.0.1:8000/login/staff/
2. Enter:
   - Username: `chef`
   - Password: `Qwertyuiop@123`
3. Click "Login"
4. **Expected**: Redirected to http://127.0.0.1:8000/chef/
5. **Result**: ✅ Chef dashboard loads

### Test Waiter Login:

1. Go to http://127.0.0.1:8000/login/staff/
2. Enter:
   - Username: `waiter`
   - Password: `Qwertyuiop@123`
3. Click "Login"
4. **Expected**: Redirected to http://127.0.0.1:8000/waiter/
5. **Result**: ✅ Waiter dashboard loads

### Test Manager Login:

1. Go to http://127.0.0.1:8000/login/staff/
2. Enter:
   - Username: `manager`
   - Password: `Admin@123`
3. Click "Login"
4. **Expected**: Redirected to http://127.0.0.1:8000/manager/
5. **Result**: ✅ Manager dashboard loads

---

## 🔍 What Changed

### Before:
```python
# Only allowed is_staff or Manager group
if mode == 'staff' and not (user.is_staff or user.groups.filter(name='Manager').exists()):
    messages.error(request, 'Staff/Manager access only.')
```

### After:
```python
# Check for Manager, Chef, or Waiter groups
is_manager = user.is_staff or user.groups.filter(name='Manager').exists()
is_chef = user.groups.filter(name='Chef').exists()
is_waiter = user.groups.filter(name='Waiter').exists()
has_staff_access = is_manager or is_chef or is_waiter

if mode == 'staff' and not has_staff_access:
    messages.error(request, 'Staff access only (Manager/Chef/Waiter).')
```

**Plus Smart Redirects**:
```python
# Redirect based on user role
if is_chef:
    return redirect('chef_dashboard')
elif is_waiter:
    return redirect('waiter_dashboard')
elif is_manager:
    return redirect('manager_dashboard')
```

---

## ✅ Benefits

1. **Single Login URL**: All staff use `/login/staff/`
2. **Automatic Redirect**: Each role goes to their dashboard
3. **No Manual Navigation**: No need to remember dashboard URLs
4. **Access Control**: Regular customers can't access staff login

---

## 🚀 Quick Test Commands

```bash
# Start server
python3 manage.py runserver

# Test in browser:
# 1. http://127.0.0.1:8000/login/staff/
# 2. Login as chef, waiter, or manager
# 3. Verify automatic redirect to correct dashboard
```

---

## 📝 Staff Credentials

| Role | Username | Password | Auto-Redirects To |
|------|----------|----------|-------------------|
| Chef | `chef` | `chef123` | `/chef/` |
| Waiter | `waiter` | `waiter123` | `/waiter/` |
| Manager | `manager` | `manager123` | `/manager/` |

---

## ❓ Troubleshooting

### Still can't login?
```bash
# Recreate users
python3 create_staff_users.py
```

### Wrong dashboard?
Clear browser cookies and login again.

### Error message?
Check that you're using correct credentials from table above.

---

**Status**: ✅ **WORKING**

All staff users (Manager, Chef, Waiter) can now login at `/login/staff/` and are automatically redirected to their appropriate dashboards!
