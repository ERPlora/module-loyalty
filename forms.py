from django import forms
from django.utils.translation import gettext_lazy as _

from .models import LoyaltyMember, LoyaltyTier, Reward


class LoyaltyMemberForm(forms.ModelForm):
    class Meta:
        model = LoyaltyMember
        fields = [
            'name', 'email', 'phone', 'card_number',
            'customer', 'tier', 'is_active', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Full name'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input',
                'placeholder': _('Email address'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Phone number'),
            }),
            'card_number': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Physical or digital card number'),
            }),
            'customer': forms.Select(attrs={
                'class': 'select',
            }),
            'tier': forms.Select(attrs={
                'class': 'select',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'toggle',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea', 'rows': 2,
            }),
        }


class LoyaltyTierForm(forms.ModelForm):
    class Meta:
        model = LoyaltyTier
        fields = [
            'name', 'name_es', 'description', 'icon', 'color',
            'min_points', 'min_spent', 'points_multiplier',
            'discount_percent', 'free_shipping', 'exclusive_offers',
            'sort_order', 'is_default', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('e.g. Bronze, Silver, Gold'),
            }),
            'name_es': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Spanish name'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea', 'rows': 2,
            }),
            'icon': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'star-outline',
            }),
            'color': forms.TextInput(attrs={
                'class': 'input', 'type': 'color',
            }),
            'min_points': forms.NumberInput(attrs={
                'class': 'input', 'min': '0',
            }),
            'min_spent': forms.NumberInput(attrs={
                'class': 'input', 'step': '0.01', 'min': '0',
            }),
            'points_multiplier': forms.NumberInput(attrs={
                'class': 'input', 'step': '0.01', 'min': '1',
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'input', 'step': '0.01', 'min': '0', 'max': '100',
            }),
            'free_shipping': forms.CheckboxInput(attrs={
                'class': 'toggle',
            }),
            'exclusive_offers': forms.CheckboxInput(attrs={
                'class': 'toggle',
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'input', 'min': '0',
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'toggle',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'toggle',
            }),
        }


class RewardForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = [
            'name', 'name_es', 'description', 'icon', 'image',
            'points_cost', 'reward_type', 'value',
            'product', 'product_name',
            'min_tier', 'max_redemptions', 'max_per_member',
            'valid_from', 'valid_until',
            'sort_order', 'is_featured', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Reward name'),
            }),
            'name_es': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Spanish name'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea', 'rows': 2,
            }),
            'icon': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'gift-outline',
            }),
            'points_cost': forms.NumberInput(attrs={
                'class': 'input', 'min': '1',
            }),
            'reward_type': forms.Select(attrs={
                'class': 'select',
            }),
            'value': forms.NumberInput(attrs={
                'class': 'input', 'step': '0.01', 'min': '0',
            }),
            'product': forms.Select(attrs={
                'class': 'select',
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Product name (for display)'),
            }),
            'min_tier': forms.Select(attrs={
                'class': 'select',
            }),
            'max_redemptions': forms.NumberInput(attrs={
                'class': 'input', 'min': '0',
                'placeholder': _('Unlimited'),
            }),
            'max_per_member': forms.NumberInput(attrs={
                'class': 'input', 'min': '1',
            }),
            'valid_from': forms.DateTimeInput(attrs={
                'class': 'input', 'type': 'datetime-local',
            }),
            'valid_until': forms.DateTimeInput(attrs={
                'class': 'input', 'type': 'datetime-local',
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'input', 'min': '0',
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'toggle',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'toggle',
            }),
        }


class MemberFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input',
            'placeholder': _('Search by name, number, email, phone...'),
        }),
    )
    tier = forms.CharField(
        required=False,
        widget=forms.Select(attrs={'class': 'select'}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('All')),
            ('active', _('Active')),
            ('inactive', _('Inactive')),
        ],
        widget=forms.Select(attrs={'class': 'select'}),
    )
