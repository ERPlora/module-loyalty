# Loyalty Module

Customer loyalty program with points, rewards, and membership tiers.

## Features

- Points-based loyalty program
- Reward redemption
- Membership tiers
- Points expiration rules
- Customer balance tracking
- Integration with Sales and Customers modules

## Installation

This module is installed automatically when activated in ERPlora Hub.

### Dependencies

- ERPlora Hub >= 1.0.0
- Required: `customers` >= 1.0.0
- Required: `sales` >= 1.0.0

## Configuration

Access module settings at `/m/loyalty/settings/`.

### Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `points_per_currency` | integer | `1` | Points earned per currency unit |
| `point_value` | decimal | `0.01` | Currency value per point |
| `points_expire` | boolean | `true` | Enable points expiration |
| `expiration_months` | integer | `12` | Months until points expire |

## Usage

### Views

| View | URL | Description |
|------|-----|-------------|
| Overview | `/m/loyalty/` | Program dashboard |
| Members | `/m/loyalty/members/` | Member list |
| Rewards | `/m/loyalty/rewards/` | Available rewards |
| Settings | `/m/loyalty/settings/` | Module configuration |

## Permissions

| Permission | Description |
|------------|-------------|
| `loyalty.view_program` | View loyalty program |
| `loyalty.manage_program` | Manage program settings |
| `loyalty.view_members` | View member balances |
| `loyalty.adjust_points` | Manually adjust points |
| `loyalty.redeem_rewards` | Process redemptions |

## Module Icon

Location: `static/icons/icon.svg`

Icon source: [React Icons - Ionicons 5](https://react-icons.github.io/react-icons/icons/io5/)

---

**Version:** 1.0.0
**Category:** customers
**Author:** ERPlora Team
