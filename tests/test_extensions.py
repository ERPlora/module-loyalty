"""
Tests for Loyalty module extension points (hooks, slots, and signals).

Tests that the loyalty module correctly:
- Registers hooks for sales.after_payment
- Registers slots for UI injection
- Listens to sale_completed and customer_created signals
- Emits loyalty-specific signals
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.core.hooks import hooks
from apps.core.slots import slots
from apps.core.signals import (
    sale_completed,
    customer_created,
    points_earned,
    points_redeemed,
    tier_changed,
)


@pytest.fixture
def cleanup_extensions():
    """Cleanup hooks and slots after each test."""
    yield
    hooks.clear_all()
    slots.clear_all()


@pytest.mark.django_db
class TestLoyaltyHooks:
    """Tests for loyalty module hook registration."""

    def setup_method(self):
        """Clear hooks before each test."""
        hooks.clear_all()

    def teardown_method(self):
        """Clear hooks after each test."""
        hooks.clear_all()

    def test_award_points_hook_registered(self):
        """Verify loyalty registers after_payment hook."""
        # Simulate what loyalty module does in ready()
        def award_points_on_sale(sale, cart, request, **kwargs):
            pass

        hooks.add_action(
            'sales.after_payment',
            award_points_on_sale,
            priority=15,
            module_id='loyalty'
        )

        assert hooks.has_action('sales.after_payment')
        registered = hooks.get_registered_hooks()
        assert any(
            h['module'] == 'loyalty'
            for h in registered['actions'].get('sales.after_payment', [])
        )

    def test_award_points_on_sale(self):
        """Verify points are awarded on sale completion."""
        points_awarded = []

        def award_points(sale, cart, request, **kwargs):
            if hasattr(sale, 'customer_id') and sale.customer_id:
                points = int(sale.total)
                points_awarded.append({
                    'customer_id': sale.customer_id,
                    'points': points
                })

        hooks.add_action('sales.after_payment', award_points, module_id='loyalty')

        # Simulate sale with customer
        sale = MagicMock()
        sale.customer_id = 123
        sale.total = Decimal('50.00')

        hooks.do_action('sales.after_payment', sale=sale, cart={}, request=None)

        assert len(points_awarded) == 1
        assert points_awarded[0]['points'] == 50

    def test_no_points_for_guest(self):
        """Verify no points for sales without customer."""
        points_awarded = []

        def award_points(sale, cart, request, **kwargs):
            if hasattr(sale, 'customer_id') and sale.customer_id:
                points_awarded.append(sale.customer_id)

        hooks.add_action('sales.after_payment', award_points, module_id='loyalty')

        # Simulate sale without customer
        sale = MagicMock()
        sale.customer_id = None
        sale.total = Decimal('50.00')

        hooks.do_action('sales.after_payment', sale=sale, cart={}, request=None)

        assert len(points_awarded) == 0


@pytest.mark.django_db
class TestLoyaltySlots:
    """Tests for loyalty module slot registration."""

    def setup_method(self):
        """Clear slots before each test."""
        slots.clear_all()

    def teardown_method(self):
        """Clear slots after each test."""
        slots.clear_all()

    def test_cart_loyalty_badge_slot_registered(self):
        """Verify loyalty registers cart header slot."""
        def get_loyalty_context(request):
            return {'loyalty_points': 150}

        def has_loyalty_customer(request):
            return request.session.get('current_customer_id') is not None

        slots.register(
            'pos.cart_header',
            template='loyalty/partials/cart_loyalty_badge.html',
            context_fn=get_loyalty_context,
            condition_fn=has_loyalty_customer,
            priority=10,
            module_id='loyalty'
        )

        assert slots.has_content('pos.cart_header')

    def test_customer_tier_badge_slot_registered(self):
        """Verify loyalty registers customer card slot."""
        slots.register(
            'customers.card_header',
            template='loyalty/partials/customer_tier_badge.html',
            priority=5,
            module_id='loyalty'
        )

        assert slots.has_content('customers.card_header')
        registered = slots.get_registered_slots()
        assert registered['customers.card_header'][0]['module'] == 'loyalty'

    def test_slot_condition_filters_content(self):
        """Verify slot condition fn filters when no customer."""
        def get_context(request):
            return {'points': 100}

        def has_customer(request):
            return request.session.get('customer_id') is not None

        slots.register(
            'pos.cart_header',
            template='loyalty/badge.html',
            context_fn=get_context,
            condition_fn=has_customer,
            module_id='loyalty'
        )

        # Request without customer
        request = MagicMock()
        request.session = {}

        content = slots.get_slot_content('pos.cart_header', request=request)
        assert len(content) == 0

        # Request with customer
        request.session = {'customer_id': 123}
        content = slots.get_slot_content('pos.cart_header', request=request)
        assert len(content) == 1


@pytest.mark.django_db
class TestLoyaltySignals:
    """Tests for loyalty module signal handling."""

    def test_points_earned_signal(self):
        """Verify points_earned signal is emitted correctly."""
        handler = MagicMock()
        points_earned.connect(handler)

        try:
            points_earned.send(
                sender='loyalty',
                member={'id': 1, 'customer_id': 123},
                points=100,
                sale={'id': 456},
                reason='purchase'
            )

            handler.assert_called_once()
            call_kwargs = handler.call_args[1]
            assert call_kwargs['points'] == 100
            assert call_kwargs['reason'] == 'purchase'
        finally:
            points_earned.disconnect(handler)

    def test_points_redeemed_signal(self):
        """Verify points_redeemed signal is emitted correctly."""
        handler = MagicMock()
        points_redeemed.connect(handler)

        try:
            points_redeemed.send(
                sender='loyalty',
                member={'id': 1},
                points=50,
                reward={'id': 1, 'name': '5 EUR off'},
                discount_amount=Decimal('5.00')
            )

            handler.assert_called_once()
            call_kwargs = handler.call_args[1]
            assert call_kwargs['points'] == 50
            assert call_kwargs['discount_amount'] == Decimal('5.00')
        finally:
            points_redeemed.disconnect(handler)

    def test_tier_changed_signal(self):
        """Verify tier_changed signal is emitted correctly."""
        handler = MagicMock()
        tier_changed.connect(handler)

        try:
            tier_changed.send(
                sender='loyalty',
                member={'id': 1},
                old_tier='Bronze',
                new_tier='Silver',
                direction='upgrade'
            )

            handler.assert_called_once()
            call_kwargs = handler.call_args[1]
            assert call_kwargs['old_tier'] == 'Bronze'
            assert call_kwargs['new_tier'] == 'Silver'
            assert call_kwargs['direction'] == 'upgrade'
        finally:
            tier_changed.disconnect(handler)

    def test_sale_completed_awards_points(self):
        """Verify listening to sale_completed triggers points award."""
        points_list = []

        def handle_sale_completed(sender, sale, user, payment_method, **kwargs):
            if hasattr(sale, 'customer_id') and sale.customer_id:
                points = int(sale.total)
                points_list.append({
                    'customer_id': sale.customer_id,
                    'points': points
                })

        sale_completed.connect(handle_sale_completed)

        try:
            sale = MagicMock()
            sale.customer_id = 123
            sale.total = Decimal('75.00')

            sale_completed.send(
                sender='sales',
                sale=sale,
                user=MagicMock(),
                payment_method='card'
            )

            assert len(points_list) == 1
            assert points_list[0]['points'] == 75
        finally:
            sale_completed.disconnect(handle_sale_completed)

    def test_customer_created_creates_member(self):
        """Verify listening to customer_created creates loyalty member."""
        members_created = []

        def handle_customer_created(sender, customer, user, **kwargs):
            members_created.append({
                'customer_id': customer['id'],
                'customer_name': customer['name']
            })

        customer_created.connect(handle_customer_created)

        try:
            customer_created.send(
                sender='customers',
                customer={'id': 456, 'name': 'New Customer'},
                user=MagicMock()
            )

            assert len(members_created) == 1
            assert members_created[0]['customer_id'] == 456
        finally:
            customer_created.disconnect(handle_customer_created)


@pytest.mark.django_db
class TestLoyaltyModuleCleanup:
    """Tests for module cleanup when deactivated."""

    def setup_method(self):
        """Setup hooks and slots."""
        hooks.clear_all()
        slots.clear_all()

    def teardown_method(self):
        """Clear all."""
        hooks.clear_all()
        slots.clear_all()

    def test_clear_module_hooks(self):
        """Verify all loyalty hooks are cleared on deactivation."""
        hooks.add_action('sales.after_payment', lambda: None, module_id='loyalty')
        hooks.add_action('sales.before_checkout', lambda: None, module_id='loyalty')
        hooks.add_action('sales.after_checkout', lambda: None, module_id='other')

        result = hooks.clear_module_hooks('loyalty')

        assert result['actions'] == 2
        assert hooks.has_action('sales.after_checkout')  # Other module remains
        assert not hooks.has_action('sales.after_payment')

    def test_clear_module_slots(self):
        """Verify all loyalty slots are cleared on deactivation."""
        slots.register('pos.cart_header', 'loyalty/badge.html', module_id='loyalty')
        slots.register('customers.card_header', 'loyalty/tier.html', module_id='loyalty')
        slots.register('pos.cart_header', 'other/badge.html', module_id='other')

        result = slots.clear_module_slots('loyalty')

        assert result == 2
        assert slots.has_content('pos.cart_header')  # Other module remains

        content = slots.get_slot_content('pos.cart_header')
        assert len(content) == 1
        assert content[0]['module_id'] == 'other'
