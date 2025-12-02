from django import forms
from .models import Item, Address


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["name", "description", "price", "image", "is_active"]


class DiningForm(forms.Form):
    name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=20)
    table_no = forms.CharField(max_length=20)


class DeliveryForm(forms.Form):
    name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)
    line1 = forms.CharField(label="Address line 1", max_length=255)
    line2 = forms.CharField(label="Address line 2", max_length=255, required=False)
    city = forms.CharField(max_length=100)
    state = forms.CharField(max_length=100, required=False)
    postal_code = forms.CharField(max_length=20, required=False)
    make_default = forms.BooleanField(required=False, initial=True)
