"""
Loyalty Module Configuration

This file defines the module metadata and navigation for the Loyalty module.
Used by the @module_view decorator to automatically render navigation tabs.
"""
from django.utils.translation import gettext_lazy as _

# Module Identification
MODULE_ID = "loyalty"
MODULE_NAME = _("Loyalty")
MODULE_ICON = "heart-outline"
MODULE_VERSION = "1.0.0"
MODULE_CATEGORY = "crm"

# Target Industries (business verticals this module is designed for)
MODULE_INDUSTRIES = [
    "retail",    # Retail stores
    "restaurant",# Restaurants
    "cafe",      # Cafes & bakeries
    "salon",     # Beauty & wellness
    "fitness",   # Fitness & sports
]

# Sidebar Menu Configuration
MENU = {
    "label": _("Loyalty"),
    "icon": "heart-outline",
    "order": 45,
    "show": True,
}

# Internal Navigation (Tabs)
NAVIGATION = [
    {
        "id": "dashboard",
        "label": _("Overview"),
        "icon": "grid-outline",
        "view": "",
    },
    {
        "id": "members",
        "label": _("Members"),
        "icon": "people-outline",
        "view": "members",
    },
    {
        "id": "rewards",
        "label": _("Rewards"),
        "icon": "gift-outline",
        "view": "rewards",
    },
    {
        "id": "tiers",
        "label": _("Tiers"),
        "icon": "ribbon-outline",
        "view": "tiers",
    },
    {
        "id": "transactions",
        "label": _("History"),
        "icon": "list-outline",
        "view": "transactions",
    },
    {
        "id": "settings",
        "label": _("Settings"),
        "icon": "settings-outline",
        "view": "settings",
    },
]

# Module Dependencies
DEPENDENCIES = []

# Default Settings
SETTINGS = {
    "program_enabled": True,
    "points_per_currency": 1.0,
    "auto_enroll": True,
}

# Permissions
PERMISSIONS = [
    "loyalty.view_loyaltymember",
    "loyalty.add_loyaltymember",
    "loyalty.change_loyaltymember",
    "loyalty.delete_loyaltymember",
    "loyalty.view_loyaltytier",
    "loyalty.add_loyaltytier",
    "loyalty.change_loyaltytier",
    "loyalty.delete_loyaltytier",
    "loyalty.view_reward",
    "loyalty.add_reward",
    "loyalty.change_reward",
    "loyalty.delete_reward",
    "loyalty.view_pointstransaction",
    "loyalty.redeem_points",
]
