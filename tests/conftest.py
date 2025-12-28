"""
Pytest fixtures for loyalty module tests.
"""

import pytest
from decimal import Decimal

from loyalty.models import (
    LoyaltyConfig,
    LoyaltyTier,
    LoyaltyMember,
    PointsTransaction,
    Reward,
    RewardRedemption,
)


@pytest.fixture
def loyalty_config():
    """Create a loyalty configuration."""
    return LoyaltyConfig.get_config()


@pytest.fixture
def bronze_tier():
    """Create a Bronze tier."""
    return LoyaltyTier.objects.create(
        name='Bronze',
        name_es='Bronce',
        icon='star-outline',
        color='#cd7f32',
        min_points=0,
        min_spent=Decimal('0.00'),
        points_multiplier=Decimal('1.00'),
        discount_percent=Decimal('0'),
        order=1,
        is_default=True,
        is_active=True,
    )


@pytest.fixture
def silver_tier():
    """Create a Silver tier."""
    return LoyaltyTier.objects.create(
        name='Silver',
        name_es='Plata',
        icon='star',
        color='#c0c0c0',
        min_points=500,
        min_spent=Decimal('100.00'),
        points_multiplier=Decimal('1.25'),
        discount_percent=Decimal('5'),
        order=2,
        is_active=True,
    )


@pytest.fixture
def gold_tier():
    """Create a Gold tier."""
    return LoyaltyTier.objects.create(
        name='Gold',
        name_es='Oro',
        icon='diamond',
        color='#ffd700',
        min_points=1000,
        min_spent=Decimal('500.00'),
        points_multiplier=Decimal('1.50'),
        discount_percent=Decimal('10'),
        free_shipping=True,
        exclusive_offers=True,
        order=3,
        is_active=True,
    )


@pytest.fixture
def loyalty_member(bronze_tier):
    """Create a loyalty member."""
    return LoyaltyMember.objects.create(
        name='John Doe',
        email='john@example.com',
        phone='555-1234',
        tier=bronze_tier,
        points_balance=100,
        lifetime_points=100,
    )


@pytest.fixture
def discount_reward():
    """Create a discount reward."""
    return Reward.objects.create(
        name='10% Off',
        name_es='10% Descuento',
        icon='pricetag-outline',
        points_cost=200,
        reward_type=Reward.RewardType.DISCOUNT_PERCENT,
        value=Decimal('10'),
        max_per_member=3,
        is_active=True,
    )


@pytest.fixture
def free_product_reward(gold_tier):
    """Create a free product reward (Gold tier only)."""
    return Reward.objects.create(
        name='Free Coffee',
        name_es='Café Gratis',
        icon='cafe-outline',
        points_cost=500,
        reward_type=Reward.RewardType.FREE_PRODUCT,
        value=Decimal('5.00'),
        product_id=1,
        product_name='Espresso',
        min_tier=gold_tier,
        max_per_member=1,
        is_active=True,
    )
