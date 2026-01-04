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
    "beauty",    # Beauty & wellness
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
# Format: (action_suffix, display_name) -> becomes "loyalty.action_suffix"
PERMISSIONS = [
    ("view_member", _("Can view loyalty members")),
    ("add_member", _("Can add loyalty members")),
    ("change_member", _("Can edit loyalty members")),
    ("delete_member", _("Can delete loyalty members")),
    ("view_tier", _("Can view loyalty tiers")),
    ("add_tier", _("Can add loyalty tiers")),
    ("change_tier", _("Can edit loyalty tiers")),
    ("delete_tier", _("Can delete loyalty tiers")),
    ("view_reward", _("Can view rewards")),
    ("add_reward", _("Can add rewards")),
    ("change_reward", _("Can edit rewards")),
    ("delete_reward", _("Can delete rewards")),
    ("view_transaction", _("Can view points transactions")),
    ("redeem_points", _("Can redeem points")),
    ("adjust_points", _("Can manually adjust points")),
]

# Role Permissions - Default permissions for each system role in this module
# Keys are role names, values are lists of permission suffixes (without module prefix)
# Use ["*"] to grant all permissions in this module
ROLE_PERMISSIONS = {
    "admin": ["*"],  # Full access to all loyalty permissions
    "manager": [
        "view_member",
        "add_member",
        "change_member",
        "view_tier",
        "add_tier",
        "change_tier",
        "view_reward",
        "add_reward",
        "change_reward",
        "view_transaction",
        "redeem_points",
        "adjust_points",
    ],
    "employee": [
        "view_member",
        "add_member",
        "view_tier",
        "view_reward",
        "view_transaction",
        "redeem_points",
    ],
}
