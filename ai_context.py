"""
AI context for the Loyalty module.
Loaded into the assistant system prompt when this module's tools are active.
"""

CONTEXT = """
## Module Knowledge: Loyalty

### Models

**LoyaltySettings** — Per-hub program configuration (singleton per hub).
- `program_name`, `program_enabled`
- `points_per_currency`: Points earned per currency unit spent (default 1.00)
- `points_value`: Currency value of one point when redeemed (default 0.01)
- `minimum_redemption`: Minimum points required to redeem (default 100)
- `points_expire` (bool), `expiry_months`
- `auto_enroll`: Auto-enroll customers on first purchase
- `welcome_points`: Bonus points on enrollment
- Use `LoyaltySettings.get_settings(hub_id)` to get or create

**LoyaltyTier** — Program tiers (e.g., Bronze, Silver, Gold).
- `name`, `name_es`, `description`
- `icon` (djicons name), `color` (hex)
- `min_points`, `min_spent`: Requirements to reach this tier
- `points_multiplier`: Multiplier on earned points (e.g., 1.5 = 50% more)
- `discount_percent`, `free_shipping`, `exclusive_offers`: Benefits
- `sort_order`, `is_default` (only one per hub), `is_active`

**LoyaltyMember** — Customer enrolled in the program.
- `member_number` (auto-generated format: LM{YYYYMM}{6-digit-seq})
- `card_number`: Physical/digital card number
- `customer` FK → customers.Customer (nullable)
- `name`, `email`, `phone`: Snapshot fields
- `tier` FK → LoyaltyTier
- `points_balance`: Current redeemable points
- `lifetime_points`: Total ever earned (used for tier upgrades)
- `total_spent`, `visit_count`
- `enrolled_at`, `last_activity_at`, `last_purchase_at`
- `is_active`
- Methods: `add_points(pts, desc, sale, employee)`, `redeem_points(pts, ...)`, `record_purchase(amount, ...)`, `check_tier_upgrade()`

**PointsTransaction** — Ledger of all points changes.
- `member` FK → LoyaltyMember
- `transaction_type`: 'earn' | 'redeem' | 'bonus' | 'adjust' | 'expire' | 'tier' | 'return'
- `points`: Positive = earned, negative = redeemed/expired
- `balance_after`: Points balance after this transaction
- `description`
- `sale` FK → sales.Sale (optional)
- `reward` FK → Reward (optional)
- `processed_by` FK → accounts.LocalUser
- `expires_at`: When these points expire (optional)

**Reward** — Redeemable rewards catalog.
- `name`, `name_es`, `description`
- `points_cost`: Points required to redeem
- `reward_type`: 'discount_percent' | 'discount_amount' | 'free_product' | 'free_shipping' | 'gift_card'
- `value`: Discount % or amount
- `product` FK → inventory.Product (for free_product rewards)
- `min_tier` FK → LoyaltyTier: Minimum tier required
- `valid_from`, `valid_until`, `max_redemptions`, `max_per_member`
- `times_redeemed`, `sort_order`, `is_active`, `is_featured`

**RewardRedemption** — Record of a specific reward redemption.
- `code` (auto-generated 8-char alphanumeric)
- `member` FK → LoyaltyMember
- `reward` FK → Reward
- `points_used`
- `status`: 'pending' | 'applied' | 'expired' | 'cancelled'
- `reward_type`, `reward_value`: Snapshots at redemption time
- `used_at`, `sale` FK → sales.Sale, `expires_at`
- Method: `apply(sale)` → sets status='applied'

### Key Flows

1. **Enroll member**: Create LoyaltyMember (auto-assigns default tier, generates member_number; welcome_points added if configured)
2. **Record purchase**: `member.record_purchase(amount, sale)` → updates total_spent, visit_count, last_purchase_at → calls `add_points()` → calls `check_tier_upgrade()`
3. **Redeem points**: `member.redeem_points(points)` → validates minimum_redemption → deducts from balance → creates PointsTransaction (type='redeem') → returns currency value
4. **Redeem reward**: Check `reward.can_redeem(member)` → create RewardRedemption (status='pending') → call `member.redeem_points(reward.points_cost)` → `redemption.apply(sale)`
5. **Tier upgrade**: Automatic on `add_points()` — checks highest eligible tier by lifetime_points or total_spent

### Relationships
- `LoyaltyMember.customer` → customers.Customer
- `PointsTransaction.sale` → sales.Sale
- `PointsTransaction.processed_by` → accounts.LocalUser
- `Reward.product` → inventory.Product
- `RewardRedemption.sale` → sales.Sale
"""
