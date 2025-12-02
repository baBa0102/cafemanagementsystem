from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import Item


@receiver(post_migrate)
def ensure_manager_group(sender, **kwargs):
    # Only run after this app's migrations
    app_label = kwargs.get("app_config").name if kwargs.get("app_config") else None
    if app_label and app_label != "cafe":
        return

    manager_group, _ = Group.objects.get_or_create(name="Manager")
    # Grant add/change/delete/view on Item to Manager
    ct = ContentType.objects.get_for_model(Item)
    perms = Permission.objects.filter(content_type=ct, codename__in=[
        "add_item", "change_item", "delete_item", "view_item",
    ])
    manager_group.permissions.add(*perms)