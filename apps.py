from django.apps import AppConfig


class LoyaltyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'loyalty'
    verbose_name = 'Loyalty Program'

    def ready(self):
        """
        Register extension points for the Loyalty module.

        This module EMITS signals:
        - points_earned: When a customer earns loyalty points
        - points_redeemed: When a customer redeems points
        - tier_changed: When a customer's tier changes

        This module LISTENS to:
        - sale_completed: To award points for purchases
        - customer_created: To auto-create loyalty member

        This module registers HOOKS:
        - sales.after_payment: Award points after successful payment
        - sales.filter_cart_items: Apply loyalty discounts

        This module registers SLOTS:
        - pos.cart_header: Show customer points badge
        - pos.totals_middle: Show redeemable rewards
        - customers.card_header: Show loyalty tier badge
        """
        self._register_hooks()
        self._register_slots()
        self._register_signal_handlers()

    def _register_hooks(self):
        """Register callbacks for hooks from other modules."""
        from apps.core.hooks import hooks

        # Award points after payment
        hooks.add_action(
            'sales.after_payment',
            self._award_points_on_sale,
            priority=15,
            module_id='loyalty'
        )

    def _register_slots(self):
        """Register UI content for slots in other modules."""
        from apps.core.slots import slots

        # Show loyalty info in cart header (if customer selected)
        slots.register(
            'pos.cart_header',
            template='loyalty/partials/cart_loyalty_badge.html',
            context_fn=self._get_loyalty_context,
            condition_fn=self._has_loyalty_customer,
            priority=10,
            module_id='loyalty'
        )

        # Show customer loyalty badge in customer cards
        slots.register(
            'customers.card_header',
            template='loyalty/partials/customer_tier_badge.html',
            context_fn=self._get_customer_loyalty_context,
            priority=5,
            module_id='loyalty'
        )

    def _register_signal_handlers(self):
        """Register handlers for signals from other modules."""
        from django.dispatch import receiver
        from apps.core.signals import sale_completed, customer_created

        @receiver(customer_created)
        def on_customer_created(sender, customer, user, **kwargs):
            """Auto-create loyalty member for new customers."""
            # from .models import LoyaltyMember
            # LoyaltyMember.objects.get_or_create(customer=customer)
            pass

    def _award_points_on_sale(self, sale, cart, request, **kwargs):
        """Hook callback: Award loyalty points after sale."""
        # Check if sale has a customer
        # if sale.customer_id:
        #     from .models import LoyaltyMember
        #     member = LoyaltyMember.objects.filter(customer_id=sale.customer_id).first()
        #     if member:
        #         points = int(sale.total)  # 1 point per currency unit
        #         member.add_points(points, reason='purchase', sale=sale)
        pass

    def _get_loyalty_context(self, request):
        """Get loyalty context for cart header slot."""
        return {
            'loyalty_points': 0,
            'loyalty_tier': None,
        }

    def _has_loyalty_customer(self, request):
        """Check if current sale has a loyalty customer."""
        # Check if customer is selected in session
        return request.session.get('current_customer_id') is not None

    def _get_customer_loyalty_context(self, context):
        """Get loyalty context for customer card slot."""
        return {
            'loyalty_tier': None,
            'loyalty_points': 0,
        }
