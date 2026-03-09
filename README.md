# Loyalty

## Overview

| Property | Value |
|----------|-------|
| **Module ID** | `loyalty` |
| **Version** | `1.0.0` |
| **Icon** | `heart-outline` |
| **Dependencies** | `customers`, `sales`, `inventory` |

## Dependencies

This module requires the following modules to be installed:

- `customers`
- `sales`
- `inventory`

## Models

### `LoyaltySettings`

Per-hub loyalty program settings.

| Field | Type | Details |
|-------|------|---------|
| `program_name` | CharField | max_length=100 |
| `program_enabled` | BooleanField |  |
| `points_per_currency` | DecimalField |  |
| `points_value` | DecimalField |  |
| `minimum_redemption` | PositiveIntegerField |  |
| `points_expire` | BooleanField |  |
| `expiry_months` | PositiveIntegerField |  |
| `auto_enroll` | BooleanField |  |
| `welcome_points` | PositiveIntegerField |  |
| `show_points_on_receipt` | BooleanField |  |
| `show_available_rewards` | BooleanField |  |

**Methods:**

- `get_settings()`
- `calculate_points()`
- `calculate_points_value()`

### `LoyaltyTier`

Loyalty program tiers (e.g., Bronze, Silver, Gold, Platinum).

| Field | Type | Details |
|-------|------|---------|
| `name` | CharField | max_length=50 |
| `name_es` | CharField | max_length=50, optional |
| `description` | TextField | optional |
| `icon` | CharField | max_length=50 |
| `color` | CharField | max_length=7 |
| `min_points` | PositiveIntegerField |  |
| `min_spent` | DecimalField |  |
| `points_multiplier` | DecimalField |  |
| `discount_percent` | DecimalField |  |
| `free_shipping` | BooleanField |  |
| `exclusive_offers` | BooleanField |  |
| `sort_order` | PositiveIntegerField |  |
| `is_default` | BooleanField |  |
| `is_active` | BooleanField |  |

**Methods:**

- `get_display_name()`

### `LoyaltyMember`

Customer enrolled in the loyalty program.

| Field | Type | Details |
|-------|------|---------|
| `member_number` | CharField | max_length=20 |
| `card_number` | CharField | max_length=30, optional |
| `customer` | ForeignKey | → `customers.Customer`, on_delete=SET_NULL, optional |
| `name` | CharField | max_length=255 |
| `email` | EmailField | max_length=254, optional |
| `phone` | CharField | max_length=20, optional |
| `tier` | ForeignKey | → `loyalty.LoyaltyTier`, on_delete=SET_NULL, optional |
| `points_balance` | PositiveIntegerField |  |
| `lifetime_points` | PositiveIntegerField |  |
| `total_spent` | DecimalField |  |
| `visit_count` | PositiveIntegerField |  |
| `enrolled_at` | DateTimeField |  |
| `last_activity_at` | DateTimeField | optional |
| `last_purchase_at` | DateTimeField | optional |
| `is_active` | BooleanField |  |
| `notes` | TextField | optional |

**Methods:**

- `add_points()`
- `redeem_points()`
- `check_tier_upgrade()`
- `record_purchase()`

**Properties:**

- `points_value`

### `PointsTransaction`

Points transaction history.

| Field | Type | Details |
|-------|------|---------|
| `member` | ForeignKey | → `loyalty.LoyaltyMember`, on_delete=CASCADE |
| `transaction_type` | CharField | max_length=20, choices: earn, redeem, bonus, adjust, expire, tier, ... |
| `points` | IntegerField |  |
| `balance_after` | PositiveIntegerField |  |
| `description` | CharField | max_length=255, optional |
| `sale` | ForeignKey | → `sales.Sale`, on_delete=SET_NULL, optional |
| `reward` | ForeignKey | → `loyalty.Reward`, on_delete=SET_NULL, optional |
| `processed_by` | ForeignKey | → `accounts.LocalUser`, on_delete=SET_NULL, optional |
| `expires_at` | DateTimeField | optional |

### `Reward`

Redeemable rewards.

| Field | Type | Details |
|-------|------|---------|
| `name` | CharField | max_length=100 |
| `name_es` | CharField | max_length=100, optional |
| `description` | TextField | optional |
| `icon` | CharField | max_length=50 |
| `image` | ImageField | max_length=100, optional |
| `points_cost` | PositiveIntegerField |  |
| `reward_type` | CharField | max_length=20, choices: discount_percent, discount_amount, free_product, free_shipping, gift_card |
| `value` | DecimalField |  |
| `product` | ForeignKey | → `inventory.Product`, on_delete=SET_NULL, optional |
| `product_name` | CharField | max_length=255, optional |
| `min_tier` | ForeignKey | → `loyalty.LoyaltyTier`, on_delete=SET_NULL, optional |
| `valid_from` | DateTimeField | optional |
| `valid_until` | DateTimeField | optional |
| `max_redemptions` | PositiveIntegerField | optional |
| `max_per_member` | PositiveIntegerField |  |
| `times_redeemed` | PositiveIntegerField |  |
| `sort_order` | PositiveIntegerField |  |
| `is_active` | BooleanField |  |
| `is_featured` | BooleanField |  |

**Methods:**

- `get_display_name()`
- `is_available()`
- `can_redeem()`

### `RewardRedemption`

Record of reward redemptions with unique codes.

| Field | Type | Details |
|-------|------|---------|
| `code` | CharField | max_length=20 |
| `member` | ForeignKey | → `loyalty.LoyaltyMember`, on_delete=CASCADE |
| `reward` | ForeignKey | → `loyalty.Reward`, on_delete=PROTECT |
| `points_used` | PositiveIntegerField |  |
| `status` | CharField | max_length=20, choices: pending, applied, expired, cancelled |
| `reward_type` | CharField | max_length=20 |
| `reward_value` | DecimalField |  |
| `used_at` | DateTimeField | optional |
| `sale` | ForeignKey | → `sales.Sale`, on_delete=SET_NULL, optional |
| `expires_at` | DateTimeField | optional |

**Methods:**

- `apply()`

## Cross-Module Relationships

| From | Field | To | on_delete | Nullable |
|------|-------|----|-----------|----------|
| `LoyaltyMember` | `customer` | `customers.Customer` | SET_NULL | Yes |
| `LoyaltyMember` | `tier` | `loyalty.LoyaltyTier` | SET_NULL | Yes |
| `PointsTransaction` | `member` | `loyalty.LoyaltyMember` | CASCADE | No |
| `PointsTransaction` | `sale` | `sales.Sale` | SET_NULL | Yes |
| `PointsTransaction` | `reward` | `loyalty.Reward` | SET_NULL | Yes |
| `PointsTransaction` | `processed_by` | `accounts.LocalUser` | SET_NULL | Yes |
| `Reward` | `product` | `inventory.Product` | SET_NULL | Yes |
| `Reward` | `min_tier` | `loyalty.LoyaltyTier` | SET_NULL | Yes |
| `RewardRedemption` | `member` | `loyalty.LoyaltyMember` | CASCADE | No |
| `RewardRedemption` | `reward` | `loyalty.Reward` | PROTECT | No |
| `RewardRedemption` | `sale` | `sales.Sale` | SET_NULL | Yes |

## URL Endpoints

Base path: `/m/loyalty/`

| Path | Name | Method |
|------|------|--------|
| `(root)` | `dashboard` | GET |
| `members/` | `members_list` | GET |
| `members/create/` | `member_create` | GET/POST |
| `members/export/csv/` | `export_members_csv` | GET |
| `members/<uuid:pk>/` | `member_detail` | GET |
| `members/<uuid:pk>/edit/` | `member_edit` | GET |
| `members/<uuid:pk>/delete/` | `member_delete` | GET/POST |
| `members/<uuid:pk>/add-points/` | `member_add_points` | GET/POST |
| `members/<uuid:pk>/redeem/` | `member_redeem` | GET |
| `tiers/` | `tiers_list` | GET |
| `tiers/create/` | `tier_create` | GET/POST |
| `tiers/<uuid:pk>/edit/` | `tier_edit` | GET |
| `tiers/<uuid:pk>/delete/` | `tier_delete` | GET/POST |
| `rewards/` | `rewards_list` | GET |
| `rewards/create/` | `reward_create` | GET/POST |
| `rewards/<uuid:pk>/` | `reward_detail` | GET |
| `rewards/<uuid:pk>/edit/` | `reward_edit` | GET |
| `rewards/<uuid:pk>/delete/` | `reward_delete` | GET/POST |
| `transactions/` | `transactions_list` | GET |
| `settings/` | `settings` | GET |
| `settings/save/` | `settings_save` | GET/POST |
| `settings/toggle/` | `settings_toggle` | GET |
| `settings/reset/` | `settings_reset` | GET |
| `api/search/` | `api_member_search` | GET |
| `api/members/<uuid:pk>/balance/` | `api_member_balance` | GET |
| `api/rewards/available/<uuid:member_id>/` | `api_available_rewards` | GET |

## Permissions

| Permission | Description |
|------------|-------------|

**Role assignments:**

- **admin**: All permissions
- **manager**: `view_member`, `add_member`, `change_member`, `view_tier`, `add_tier`, `change_tier`, `view_reward`, `add_reward` (+4 more)
- **employee**: `view_member`, `add_member`, `view_tier`, `view_reward`, `view_transaction`, `redeem_points`

## Navigation

| View | Icon | ID | Fullpage |
|------|------|----|----------|
| Overview | `grid-outline` | `dashboard` | No |
| Members | `people-outline` | `members` | No |
| Rewards | `gift-outline` | `rewards` | No |
| Tiers | `ribbon-outline` | `tiers` | No |
| History | `list-outline` | `transactions` | No |
| Settings | `settings-outline` | `settings` | No |

## AI Tools

Tools available for the AI assistant:

### `list_loyalty_members`

List loyalty program members with optional search.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search` | string | No | Search by name, email, or member number |
| `tier_id` | string | No | Filter by tier ID |
| `limit` | integer | No | Max results (default 20) |

### `get_loyalty_member`

Get detailed info for a loyalty member by ID or member number.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `member_id` | string | No | Member ID |
| `member_number` | string | No | Member number |

### `award_loyalty_points`

Award bonus points to a loyalty member.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `member_id` | string | Yes | Member ID |
| `points` | integer | Yes | Points to award |
| `description` | string | No | Reason for bonus points |

### `list_rewards`

List available loyalty rewards.

## Hooks

**Emits (other modules can listen):**

- `sales.after_payment` (action) — in `test_extensions.py`

**Listens to (hooks from other modules):**

- `sales.after_payment` (action) — in `test_extensions.py`
- `sales.before_checkout` (action) — in `test_extensions.py`
- `sales.after_checkout` (action) — in `test_extensions.py`

## Signals

**Emits:**

- `points_earned` — in `test_extensions.py`
- `points_redeemed` — in `test_extensions.py`
- `tier_changed` — in `test_extensions.py`
- `sale_completed` — in `test_extensions.py`
- `customer_created` — in `test_extensions.py`

## File Structure

```
CHANGELOG.md
README.md
TODO.md
__init__.py
admin.py
ai_tools.py
apps.py
forms.py
locale/
  es/
    LC_MESSAGES/
      django.po
migrations/
  0001_initial.py
  __init__.py
models.py
module.py
static/
  icons/
    ion/
templates/
  loyalty/
    pages/
      index.html
      member_add_points.html
      member_detail.html
      member_form.html
      member_redeem.html
      members.html
      reward_detail.html
      reward_form.html
      rewards.html
      settings.html
      tier_form.html
      tiers.html
      transactions.html
    partials/
      dashboard_content.html
      member_add_points.html
      member_detail.html
      member_form.html
      member_redeem.html
      members_list.html
      reward_detail.html
      reward_form.html
      rewards_list.html
      settings_form.html
      tier_form.html
      tiers_list.html
      transactions_list.html
tests/
  __init__.py
  test_extensions.py
  test_models.py
  test_views.py
urls.py
views.py
```
