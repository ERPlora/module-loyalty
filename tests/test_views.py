"""
Integration tests for Loyalty module views.
"""

import pytest
import json
from decimal import Decimal
from django.test import Client

from loyalty.models import (
    LoyaltyConfig,
    LoyaltyTier,
    LoyaltyMember,
    PointsTransaction,
    Reward,
)


@pytest.fixture
def client():
    """Create test client."""
    return Client()


@pytest.fixture
def loyalty_config():
    """Create loyalty configuration."""
    return LoyaltyConfig.get_config()


@pytest.fixture
def sample_tier(loyalty_config):
    """Create a sample tier."""
    return LoyaltyTier.objects.create(
        name="Gold",
        min_points=1000,
        multiplier=Decimal("1.5"),
        order=1
    )


@pytest.fixture
def sample_member(sample_tier):
    """Create a sample loyalty member."""
    return LoyaltyMember.objects.create(
        name="Test Member",
        email="member@example.com",
        phone="+34600123456",
        current_points=500,
        lifetime_points=500,
        tier=sample_tier
    )


@pytest.fixture
def sample_reward(loyalty_config):
    """Create a sample reward."""
    return Reward.objects.create(
        name="Free Coffee",
        description="One free coffee",
        points_required=100,
        is_active=True
    )


@pytest.mark.django_db
class TestLoyaltyDashboard:
    """Tests for loyalty dashboard view."""

    def test_dashboard_get(self, client, loyalty_config):
        """Test GET dashboard."""
        response = client.get('/modules/loyalty/')

        assert response.status_code == 200

    def test_dashboard_htmx(self, client, loyalty_config):
        """Test HTMX request returns partial."""
        response = client.get(
            '/modules/loyalty/',
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestMemberListView:
    """Tests for member list view."""

    def test_members_list_get(self, client, loyalty_config):
        """Test GET members list."""
        response = client.get('/modules/loyalty/members/')

        assert response.status_code == 200

    def test_members_list_with_member(self, client, sample_member):
        """Test list with existing member."""
        response = client.get('/modules/loyalty/members/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestMemberCreateView:
    """Tests for member create view."""

    def test_create_get_form(self, client, loyalty_config):
        """Test GET create form."""
        response = client.get('/modules/loyalty/members/create/')

        assert response.status_code == 200

    def test_create_member_success(self, client, loyalty_config):
        """Test POST create member."""
        response = client.post('/modules/loyalty/members/create/', {
            'name': 'New Member',
            'email': 'new@example.com',
            'phone': '+34600111222'
        })

        # Should redirect or return success
        assert response.status_code in [200, 302]


@pytest.mark.django_db
class TestMemberDetailView:
    """Tests for member detail view."""

    def test_detail_view(self, client, sample_member):
        """Test GET member detail."""
        response = client.get(f'/modules/loyalty/members/{sample_member.id}/')

        assert response.status_code == 200

    def test_detail_view_not_found(self, client, loyalty_config):
        """Test GET member not found."""
        response = client.get('/modules/loyalty/members/99999/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestTiersView:
    """Tests for tiers views."""

    def test_tiers_list(self, client, sample_tier):
        """Test GET tiers list."""
        response = client.get('/modules/loyalty/tiers/')

        assert response.status_code == 200

    def test_tier_create_form(self, client, loyalty_config):
        """Test GET tier create form."""
        response = client.get('/modules/loyalty/tiers/create/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestRewardsView:
    """Tests for rewards views."""

    def test_rewards_list(self, client, sample_reward):
        """Test GET rewards list."""
        response = client.get('/modules/loyalty/rewards/')

        assert response.status_code == 200

    def test_reward_detail(self, client, sample_reward):
        """Test GET reward detail."""
        response = client.get(f'/modules/loyalty/rewards/{sample_reward.id}/')

        assert response.status_code == 200

    def test_reward_create_form(self, client, loyalty_config):
        """Test GET reward create form."""
        response = client.get('/modules/loyalty/rewards/create/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestTransactionsView:
    """Tests for transactions view."""

    def test_transactions_list(self, client, loyalty_config):
        """Test GET transactions list."""
        response = client.get('/modules/loyalty/transactions/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestSettingsView:
    """Tests for settings view."""

    def test_settings_get(self, client, loyalty_config):
        """Test GET settings."""
        response = client.get('/modules/loyalty/settings/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestAPIEndpoints:
    """Tests for API endpoints."""

    def test_api_member_search(self, client, sample_member):
        """Test member search API."""
        response = client.get('/modules/loyalty/api/search/?q=Test')

        assert response.status_code == 200

    def test_api_member_balance(self, client, sample_member):
        """Test member balance API."""
        response = client.get(f'/modules/loyalty/api/members/{sample_member.id}/balance/')

        assert response.status_code == 200

    def test_api_available_rewards(self, client, sample_member, sample_reward):
        """Test available rewards API."""
        response = client.get(f'/modules/loyalty/api/rewards/available/{sample_member.id}/')

        assert response.status_code == 200
