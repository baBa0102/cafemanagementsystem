#!/usr/bin/env python
"""
Script to create Chef and Waiter user groups and test users
Run: python3 create_staff_users.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafemanagementsystem.settings')
django.setup()

from django.contrib.auth.models import Group, User

def create_groups_and_users():
    print("🔧 Creating user groups and staff users...")
    
    # Create groups
    chef_group, created = Group.objects.get_or_create(name='Chef')
    if created:
        print("✓ Created 'Chef' group")
    else:
        print("  'Chef' group already exists")
    
    waiter_group, created = Group.objects.get_or_create(name='Waiter')
    if created:
        print("✓ Created 'Waiter' group")
    else:
        print("  'Waiter' group already exists")
    
    manager_group, created = Group.objects.get_or_create(name='Manager')
    if created:
        print("✓ Created 'Manager' group")
    else:
        print("  'Manager' group already exists")
    
    # Create chef user
    chef_user, created = User.objects.get_or_create(
        username='chef',
        defaults={
            'first_name': 'Head',
            'last_name': 'Chef',
            'is_staff': False
        }
    )
    if created:
        chef_user.set_password('chef123')
        chef_user.save()
        chef_user.groups.add(chef_group)
        print("✓ Created chef user (username: chef, password: chef123)")
    else:
        print("  chef user already exists")
        if not chef_user.groups.filter(name='Chef').exists():
            chef_user.groups.add(chef_group)
            print("  Added chef to Chef group")
    
    # Create waiter user
    waiter_user, created = User.objects.get_or_create(
        username='waiter',
        defaults={
            'first_name': 'Service',
            'last_name': 'Staff',
            'is_staff': False
        }
    )
    if created:
        waiter_user.set_password('waiter123')
        waiter_user.save()
        waiter_user.groups.add(waiter_group)
        print("✓ Created waiter user (username: waiter, password: waiter123)")
    else:
        print("  waiter user already exists")
        if not waiter_user.groups.filter(name='Waiter').exists():
            waiter_user.groups.add(waiter_group)
            print("  Added waiter to Waiter group")
    
    # Ensure manager user exists and is in Manager group
    try:
        manager_user = User.objects.get(username='manager')
        if not manager_user.groups.filter(name='Manager').exists():
            manager_user.groups.add(manager_group)
            print("✓ Added manager to Manager group")
    except User.DoesNotExist:
        manager_user = User.objects.create_user(
            username='manager',
            password='manager123',
            first_name='Manager',
            last_name='Admin',
            is_staff=True
        )
        manager_user.groups.add(manager_group)
        print("✓ Created manager user (username: manager, password: manager123)")
    
    print("\n✅ Setup complete!")
    print("\n📝 Login Credentials:")
    print("   Manager: username=manager, password=manager123")
    print("   Chef: username=chef, password=chef123")
    print("   Waiter: username=waiter, password=waiter123")
    print("\n🔗 Access URLs:")
    print("   Manager Dashboard: http://127.0.0.1:8000/manager/")
    print("   Chef Dashboard: http://127.0.0.1:8000/chef/")
    print("   Waiter Dashboard: http://127.0.0.1:8000/waiter/")

if __name__ == "__main__":
    create_groups_and_users()
