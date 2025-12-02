#!/usr/bin/env python3
"""
Setup script to create Manager group and test manager user
Run: python3 manage.py shell < setup_manager.py
Or: python3 setup_manager.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafemanagementsystem.settings')
django.setup()

from django.contrib.auth.models import User, Group

def setup_manager_group():
    """Create Manager group if it doesn't exist"""
    group, created = Group.objects.get_or_create(name='Manager')
    if created:
        print("✓ Created 'Manager' group")
    else:
        print("✓ 'Manager' group already exists")
    return group

def create_test_manager(username='manager', email='manager@cafe.com', password='manager123'):
    """Create a test manager user"""
    try:
        # Check if user exists
        user = User.objects.get(username=username)
        print(f"✓ User '{username}' already exists")
    except User.DoesNotExist:
        # Create new user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_staff = True
        user.save()
        print(f"✓ Created manager user: {username}")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
    
    # Add to Manager group
    manager_group = Group.objects.get(name='Manager')
    user.groups.add(manager_group)
    user.save()
    print(f"✓ Added '{username}' to Manager group")
    
    return user

def main():
    print("\n=== Cafe Management System - Manager Setup ===\n")
    
    # Step 1: Create Manager group
    print("Step 1: Setting up Manager group...")
    setup_manager_group()
    
    # Step 2: Create test manager
    print("\nStep 2: Creating test manager user...")
    create_test_manager()
    
    print("\n=== Setup Complete! ===")
    print("\nYou can now login as manager:")
    print("  URL: http://127.0.0.1:8000/login/staff/")
    print("  Username: manager")
    print("  Password: manager123")
    print("\nManager Dashboard: http://127.0.0.1:8000/manager/")
    print()

if __name__ == '__main__':
    main()
