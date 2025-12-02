#!/usr/bin/env python
"""
Seed script to create item categories and sample items
Run: python3 seed_items.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafemanagementsystem.settings')
django.setup()

from cafe.models import ItemCategory, Item

def seed_data():
    print("🌱 Seeding item categories and items...")
    
    # Create categories
    beverages, _ = ItemCategory.objects.get_or_create(
        name="Beverages",
        defaults={
            "description": "Hot and cold drinks",
            "display_order": 1
        }
    )
    print(f"✓ Category: {beverages.name}")
    
    snacks, _ = ItemCategory.objects.get_or_create(
        name="Snacks",
        defaults={
            "description": "Quick bites and appetizers",
            "display_order": 2
        }
    )
    print(f"✓ Category: {snacks.name}")
    
    rice, _ = ItemCategory.objects.get_or_create(
        name="Rice",
        defaults={
            "description": "Rice dishes and biryanis",
            "display_order": 3
        }
    )
    print(f"✓ Category: {rice.name}")
    
    # Beverages items (Chandigarh prices)
    beverages_items = [
        {"name": "Filter Coffee", "price": 60, "description": "South Indian filter coffee"},
        {"name": "Cappuccino", "price": 80, "description": "Classic Italian cappuccino"},
        {"name": "Cold Coffee", "price": 90, "description": "Chilled coffee with ice cream"},
        {"name": "Masala Chai", "price": 40, "description": "Indian spiced tea"},
        {"name": "Mango Mocktail", "price": 120, "description": "Fresh mango mocktail"},
        {"name": "Virgin Mojito", "price": 110, "description": "Minty lime mocktail"},
        {"name": "Blue Lagoon", "price": 130, "description": "Blue curacao mocktail"},
        {"name": "Fresh Lime Soda", "price": 50, "description": "Sweet or salted lime soda"},
    ]
    
    for item_data in beverages_items:
        item, created = Item.objects.get_or_create(
            name=item_data["name"],
            category=beverages,
            defaults={
                "description": item_data["description"],
                "price": item_data["price"],
                "is_active": True
            }
        )
        if created:
            print(f"  ✓ Added: {item.name} - ₹{item.price}")
    
    # Snacks items (Chandigarh prices)
    snacks_items = [
        {"name": "Spring Rolls", "price": 120, "description": "Crispy vegetable spring rolls"},
        {"name": "Samosa", "price": 30, "description": "Classic Indian samosa"},
        {"name": "Paneer Tikka", "price": 180, "description": "Grilled cottage cheese cubes"},
        {"name": "French Fries", "price": 80, "description": "Crispy golden fries"},
        {"name": "Veg Manchurian", "price": 140, "description": "Indo-Chinese veggie balls"},
        {"name": "Chilli Paneer", "price": 160, "description": "Spicy paneer in Chinese style"},
        {"name": "Garlic Bread", "price": 100, "description": "Toasted bread with garlic butter"},
        {"name": "Onion Rings", "price": 90, "description": "Crispy battered onion rings"},
    ]
    
    for item_data in snacks_items:
        item, created = Item.objects.get_or_create(
            name=item_data["name"],
            category=snacks,
            defaults={
                "description": item_data["description"],
                "price": item_data["price"],
                "is_active": True
            }
        )
        if created:
            print(f"  ✓ Added: {item.name} - ₹{item.price}")
    
    # Rice items (Chandigarh prices)
    rice_items = [
        {"name": "Veg Biryani", "price": 180, "description": "Aromatic vegetable biryani"},
        {"name": "Paneer Biryani", "price": 220, "description": "Biryani with cottage cheese"},
        {"name": "Jeera Rice", "price": 100, "description": "Cumin flavored rice"},
        {"name": "Veg Fried Rice", "price": 140, "description": "Chinese style fried rice"},
        {"name": "Schezwan Rice", "price": 160, "description": "Spicy Schezwan fried rice"},
        {"name": "Curd Rice", "price": 90, "description": "Rice with yogurt and tempering"},
        {"name": "Pulao", "price": 130, "description": "Mildly spiced rice"},
        {"name": "Hyderabadi Biryani", "price": 250, "description": "Authentic Hyderabadi style biryani"},
    ]
    
    for item_data in rice_items:
        item, created = Item.objects.get_or_create(
            name=item_data["name"],
            category=rice,
            defaults={
                "description": item_data["description"],
                "price": item_data["price"],
                "is_active": True
            }
        )
        if created:
            print(f"  ✓ Added: {item.name} - ₹{item.price}")
    
    print(f"\n✅ Seeding complete!")
    print(f"   Beverages: {Item.objects.filter(category=beverages).count()} items")
    print(f"   Snacks: {Item.objects.filter(category=snacks).count()} items")
    print(f"   Rice: {Item.objects.filter(category=rice).count()} items")

if __name__ == "__main__":
    seed_data()
