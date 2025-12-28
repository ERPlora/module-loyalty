"""
Tests for loyalty module models.
"""

import pytest
from decimal import Decimal
from django.utils import timezone

from loyalty.models import (
    LoyaltyConfig,
    LoyaltyTier,
    LoyaltyMember,
    PointsTransaction,
    Reward,
    RewardRedemption,
)


@pytest.mark.django_db
class TestLoyaltyConfig:
    """Tests for LoyaltyConfig model."""

    def test_singleton_pattern(self):
        """Test that only one config exists."""
        config1 = LoyaltyConfig.get_config()
        config2 = LoyaltyConfig.get_config()
        assert config1.pk == config2.pk == 1

    def test_default_values(self, loyalty_config):
        """Test default configuration values."""
        assert loyalty_config.program_enabled is True
        assert loyalty_config.points_per_currency == Decimal('1.00')
        assert loyalty_config.points_value == Decimal('0.01')
        assert loyalty_config.auto_enroll is True

    def test_calculate_points(self, loyalty_config):
        """Test points calculation."""
        assert loyalty_config.calculate_points(Decimal('100.00')) == 100
        assert loyalty_config.calculate_points(Decimal('50.50')) == 50

    def test_calculate_points_value(self, loyalty_config):
        """Test points value calculation."""
        assert loyalty_config.calculate_points_value(100) == Decimal('1.00')
        assert loyalty_config.calculate_points_value(500) == Decimal('5.00')


@pytest.mark.django_db
class TestLoyaltyTier:
    """Tests for LoyaltyTier model."""

    def test_create_tier(self, bronze_tier):
        """Test tier creation."""
        assert bronze_tier.name == 'Bronze'
        assert bronze_tier.is_default is True
        assert bronze_tier.is_active is True

    def test_get_display_name(self, bronze_tier):
        """Test localized name."""
        assert bronze_tier.get_display_name('en') == 'Bronze'
        assert bronze_tier.get_display_name('es') == 'Bronce'

    def test_only_one_default(self, bronze_tier, silver_tier):
        """Test only one tier can be default."""
        silver_tier.is_default = True
        silver_tier.save()
        bronze_tier.refresh_from_db()
        assert bronze_tier.is_default is False
        assert silver_tier.is_default is True


@pytest.mark.django_db
class TestLoyaltyMember:
    """Tests for LoyaltyMember model."""

    def test_auto_generate_member_number(self, bronze_tier):
        """Test automatic member number generation."""
        member = LoyaltyMember.objects.create(
            name='Test User',
            tier=bronze_tier,
        )
        assert member.member_number.startswith('LM')

    def test_add_points(self, loyalty_member):
        """Test adding points to member."""
        initial_balance = loyalty_member.points_balance
        loyalty_member.add_points(50, description='Test bonus')
        assert loyalty_member.points_balance == initial_balance + 50
        assert loyalty_member.lifetime_points == initial_balance + 50

        # Check transaction created
        tx = PointsTransaction.objects.filter(
            member=loyalty_member,
            transaction_type=PointsTransaction.Type.EARN
        ).last()
        assert tx is not None
        assert tx.points == 50

    def test_add_points_with_multiplier(self, loyalty_member, gold_tier):
        """Test points multiplier from tier."""
        loyalty_member.tier = gold_tier  # 1.5x multiplier
        loyalty_member.save()
        initial_balance = loyalty_member.points_balance
        earned = loyalty_member.add_points(100, description='Purchase')
        assert earned == 150  # 100 * 1.5
        assert loyalty_member.points_balance == initial_balance + 150

    def test_redeem_points(self, loyalty_member, loyalty_config):
        """Test redeeming points."""
        loyalty_member.points_balance = 500
        loyalty_member.save()

        value = loyalty_member.redeem_points(200, description='Reward redemption')
        assert value == Decimal('2.00')  # 200 * 0.01
        assert loyalty_member.points_balance == 300

        # Check transaction created
        tx = PointsTransaction.objects.filter(
            member=loyalty_member,
            transaction_type=PointsTransaction.Type.REDEEM
        ).last()
        assert tx is not None
        assert tx.points == -200

    def test_redeem_insufficient_points(self, loyalty_member):
        """Test redemption fails with insufficient points."""
        with pytest.raises(ValueError):
            loyalty_member.redeem_points(1000)  # More than balance

    def test_tier_upgrade(self, loyalty_member, silver_tier, gold_tier):
        """Test automatic tier upgrade."""
        loyalty_member.lifetime_points = 1000  # Meets gold requirements
        loyalty_member.check_tier_upgrade()
        loyalty_member.refresh_from_db()
        assert loyalty_member.tier == gold_tier

    def test_record_purchase(self, loyalty_member, loyalty_config):
        """Test recording a purchase."""
        initial_visits = loyalty_member.visit_count
        initial_spent = loyalty_member.total_spent

        points = loyalty_member.record_purchase(Decimal('100.00'))

        assert points == 100
        assert loyalty_member.visit_count == initial_visits + 1
        assert loyalty_member.total_spent == initial_spent + Decimal('100.00')
        assert loyalty_member.last_purchase_at is not None


@pytest.mark.django_db
class TestPointsTransaction:
    """Tests for PointsTransaction model."""

    def test_create_transaction(self, loyalty_member):
        """Test transaction creation."""
        tx = PointsTransaction.objects.create(
            member=loyalty_member,
            transaction_type=PointsTransaction.Type.BONUS,
            points=100,
            balance_after=200,
            description='Birthday bonus',
        )
        assert tx.id is not None
        assert tx.points == 100


@pytest.mark.django_db
class TestReward:
    """Tests for Reward model."""

    def test_create_reward(self, discount_reward):
        """Test reward creation."""
        assert discount_reward.name == '10% Off'
        assert discount_reward.points_cost == 200
        assert discount_reward.reward_type == Reward.RewardType.DISCOUNT_PERCENT

    def test_is_available(self, discount_reward):
        """Test reward availability check."""
        assert discount_reward.is_available() is True

        discount_reward.is_active = False
        assert discount_reward.is_available() is False

    def test_can_redeem(self, discount_reward, loyalty_member):
        """Test member can redeem reward."""
        loyalty_member.points_balance = 500  # Enough points
        loyalty_member.save()

        can, reason = discount_reward.can_redeem(loyalty_member)
        assert can is True
        assert reason is None

    def test_cannot_redeem_insufficient_points(self, discount_reward, loyalty_member):
        """Test cannot redeem with insufficient points."""
        loyalty_member.points_balance = 50  # Not enough
        loyalty_member.save()

        can, reason = discount_reward.can_redeem(loyalty_member)
        assert can is False
        assert 'points' in str(reason).lower()

    def test_cannot_redeem_tier_requirement(self, free_product_reward, loyalty_member):
        """Test cannot redeem without required tier."""
        loyalty_member.points_balance = 1000
        loyalty_member.save()

        can, reason = free_product_reward.can_redeem(loyalty_member)
        assert can is False
        assert 'tier' in str(reason).lower()


@pytest.mark.django_db
class TestRewardRedemption:
    """Tests for RewardRedemption model."""

    def test_auto_generate_code(self, discount_reward, loyalty_member):
        """Test automatic redemption code generation."""
        redemption = RewardRedemption.objects.create(
            member=loyalty_member,
            reward=discount_reward,
            points_used=discount_reward.points_cost,
            reward_type=discount_reward.reward_type,
            reward_value=discount_reward.value,
        )
        assert len(redemption.code) == 8
        assert redemption.status == RewardRedemption.Status.PENDING

    def test_apply_redemption(self, discount_reward, loyalty_member):
        """Test applying a redemption to a sale."""
        redemption = RewardRedemption.objects.create(
            member=loyalty_member,
            reward=discount_reward,
            points_used=discount_reward.points_cost,
            reward_type=discount_reward.reward_type,
            reward_value=discount_reward.value,
        )

        redemption.apply(sale_id=123)

        assert redemption.status == RewardRedemption.Status.APPLIED
        assert redemption.sale_id == 123
        assert redemption.used_at is not None
