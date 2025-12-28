"""
Loyalty Module Models
Customer loyalty programs, points accumulation, tiers, and rewards.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class LoyaltyConfig(models.Model):
    """
    Singleton configuration for loyalty module.
    """
    # Program settings
    program_name = models.CharField(
        _('Program Name'),
        max_length=100,
        default='Loyalty Program'
    )
    program_enabled = models.BooleanField(
        _('Program Enabled'),
        default=True
    )

    # Points settings
    points_per_currency = models.DecimalField(
        _('Points per Currency Unit'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text=_('Points earned per currency unit spent (e.g., 1 point per €1)')
    )
    points_value = models.DecimalField(
        _('Point Value'),
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.01'),
        help_text=_('Currency value of each point when redeemed')
    )
    minimum_redemption = models.PositiveIntegerField(
        _('Minimum Points for Redemption'),
        default=100,
        help_text=_('Minimum points required to redeem')
    )

    # Expiry settings
    points_expire = models.BooleanField(
        _('Points Expire'),
        default=False
    )
    expiry_months = models.PositiveIntegerField(
        _('Expiry Period (Months)'),
        default=12,
        help_text=_('Months after earning before points expire')
    )

    # Enrollment settings
    auto_enroll = models.BooleanField(
        _('Auto-Enroll Customers'),
        default=True,
        help_text=_('Automatically enroll customers on first purchase')
    )
    welcome_points = models.PositiveIntegerField(
        _('Welcome Points'),
        default=0,
        help_text=_('Bonus points given on enrollment')
    )

    # Display settings
    show_points_on_receipt = models.BooleanField(
        _('Show Points on Receipt'),
        default=True
    )
    show_available_rewards = models.BooleanField(
        _('Show Available Rewards at Checkout'),
        default=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'loyalty'
        db_table = 'loyalty_config'
        verbose_name = _('Loyalty Configuration')
        verbose_name_plural = _('Loyalty Configuration')

    def __str__(self):
        return self.program_name

    @classmethod
    def get_config(cls):
        """Get or create the singleton config."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def save(self, *args, **kwargs):
        self.pk = 1  # Ensure singleton
        super().save(*args, **kwargs)

    def calculate_points(self, amount):
        """Calculate points for a given purchase amount."""
        return int(amount * self.points_per_currency)

    def calculate_points_value(self, points):
        """Calculate currency value of points."""
        return points * self.points_value


class LoyaltyTier(models.Model):
    """
    Loyalty program tiers (e.g., Bronze, Silver, Gold, Platinum).
    """
    name = models.CharField(_('Name'), max_length=50)
    name_es = models.CharField(_('Name (Spanish)'), max_length=50, blank=True)
    description = models.TextField(_('Description'), blank=True)

    # Visual
    icon = models.CharField(_('Icon'), max_length=50, default='star-outline')
    color = models.CharField(_('Color'), max_length=7, default='#cd7f32')  # Bronze

    # Requirements
    min_points = models.PositiveIntegerField(
        _('Minimum Points'),
        default=0,
        help_text=_('Points required to reach this tier')
    )
    min_spent = models.DecimalField(
        _('Minimum Spent'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Total spent required to reach this tier')
    )

    # Benefits
    points_multiplier = models.DecimalField(
        _('Points Multiplier'),
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text=_('Multiplier for points earned (e.g., 1.5 = 50% more points)')
    )
    discount_percent = models.DecimalField(
        _('Discount %'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text=_('Automatic discount for this tier')
    )
    free_shipping = models.BooleanField(
        _('Free Shipping'),
        default=False
    )
    exclusive_offers = models.BooleanField(
        _('Exclusive Offers'),
        default=False
    )

    # Ordering
    order = models.PositiveIntegerField(_('Order'), default=0)
    is_default = models.BooleanField(
        _('Default Tier'),
        default=False,
        help_text=_('Tier assigned to new members')
    )
    is_active = models.BooleanField(_('Active'), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'loyalty'
        db_table = 'loyalty_tier'
        verbose_name = _('Loyalty Tier')
        verbose_name_plural = _('Loyalty Tiers')
        ordering = ['order', 'min_points']

    def __str__(self):
        return self.name

    def get_display_name(self, language='en'):
        """Get localized name."""
        if language == 'es' and self.name_es:
            return self.name_es
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one default tier
        if self.is_default:
            LoyaltyTier.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class LoyaltyMember(models.Model):
    """
    Customer enrolled in the loyalty program.
    Links to Customer module if available.
    """
    # Member identification
    member_number = models.CharField(
        _('Member Number'),
        max_length=20,
        unique=True
    )
    card_number = models.CharField(
        _('Card Number'),
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Physical or digital card number')
    )

    # Link to customer (optional - may not have customers module)
    customer_id = models.PositiveIntegerField(
        _('Customer ID'),
        null=True,
        blank=True,
        help_text=_('ID from customers module')
    )

    # Customer info (copied for standalone use)
    name = models.CharField(_('Name'), max_length=255)
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Phone'), max_length=20, blank=True)

    # Loyalty status
    tier = models.ForeignKey(
        LoyaltyTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name=_('Tier')
    )
    points_balance = models.PositiveIntegerField(
        _('Points Balance'),
        default=0
    )
    lifetime_points = models.PositiveIntegerField(
        _('Lifetime Points Earned'),
        default=0
    )
    total_spent = models.DecimalField(
        _('Total Spent'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    visit_count = models.PositiveIntegerField(
        _('Visit Count'),
        default=0
    )

    # Dates
    enrolled_at = models.DateTimeField(_('Enrolled At'), auto_now_add=True)
    last_activity_at = models.DateTimeField(_('Last Activity'), null=True, blank=True)
    last_purchase_at = models.DateTimeField(_('Last Purchase'), null=True, blank=True)

    # Status
    is_active = models.BooleanField(_('Active'), default=True)
    notes = models.TextField(_('Notes'), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'loyalty'
        db_table = 'loyalty_member'
        verbose_name = _('Loyalty Member')
        verbose_name_plural = _('Loyalty Members')
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['member_number']),
            models.Index(fields=['card_number']),
            models.Index(fields=['customer_id']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f'{self.name} ({self.member_number})'

    def save(self, *args, **kwargs):
        if not self.member_number:
            self.member_number = self._generate_member_number()

        # Assign default tier if not set
        if not self.tier_id:
            default_tier = LoyaltyTier.objects.filter(is_default=True, is_active=True).first()
            if default_tier:
                self.tier = default_tier

        super().save(*args, **kwargs)

    def _generate_member_number(self):
        """Generate unique member number."""
        today = timezone.now().strftime('%Y%m')
        last_member = LoyaltyMember.objects.filter(
            member_number__startswith=f'LM{today}'
        ).order_by('-member_number').first()

        if last_member:
            last_num = int(last_member.member_number[-6:])
            new_num = last_num + 1
        else:
            new_num = 1

        return f'LM{today}{new_num:06d}'

    def add_points(self, points, description='', sale_id=None):
        """Add points to member balance."""
        if points <= 0:
            return

        # Apply tier multiplier
        if self.tier and self.tier.points_multiplier > 1:
            points = int(points * self.tier.points_multiplier)

        self.points_balance += points
        self.lifetime_points += points
        self.last_activity_at = timezone.now()
        self.save()

        # Create transaction
        PointsTransaction.objects.create(
            member=self,
            transaction_type=PointsTransaction.Type.EARN,
            points=points,
            balance_after=self.points_balance,
            description=description,
            sale_id=sale_id,
        )

        # Check for tier upgrade
        self.check_tier_upgrade()

        return points

    def redeem_points(self, points, description='', sale_id=None):
        """Redeem points from member balance."""
        if points <= 0 or points > self.points_balance:
            raise ValueError(_('Insufficient points balance'))

        config = LoyaltyConfig.get_config()
        if points < config.minimum_redemption:
            raise ValueError(_('Minimum %(min)s points required') % {'min': config.minimum_redemption})

        self.points_balance -= points
        self.last_activity_at = timezone.now()
        self.save()

        # Create transaction
        PointsTransaction.objects.create(
            member=self,
            transaction_type=PointsTransaction.Type.REDEEM,
            points=-points,
            balance_after=self.points_balance,
            description=description,
            sale_id=sale_id,
        )

        return config.calculate_points_value(points)

    def check_tier_upgrade(self):
        """Check and upgrade tier based on points/spending."""
        eligible_tiers = LoyaltyTier.objects.filter(
            is_active=True
        ).filter(
            models.Q(min_points__lte=self.lifetime_points) |
            models.Q(min_spent__lte=self.total_spent)
        ).order_by('-min_points', '-min_spent')

        if eligible_tiers.exists():
            new_tier = eligible_tiers.first()
            if not self.tier or new_tier.min_points > self.tier.min_points:
                old_tier = self.tier
                self.tier = new_tier
                self.save()

                # Log tier change
                PointsTransaction.objects.create(
                    member=self,
                    transaction_type=PointsTransaction.Type.TIER_CHANGE,
                    points=0,
                    balance_after=self.points_balance,
                    description=f'Tier upgrade: {old_tier.name if old_tier else "None"} → {new_tier.name}',
                )

    def record_purchase(self, amount, sale_id=None):
        """Record a purchase and earn points."""
        self.total_spent += amount
        self.visit_count += 1
        self.last_purchase_at = timezone.now()
        self.save()

        # Calculate and add points
        config = LoyaltyConfig.get_config()
        points = config.calculate_points(amount)
        if points > 0:
            self.add_points(points, description=f'Purchase: {amount}', sale_id=sale_id)

        return points

    @property
    def points_value(self):
        """Get currency value of current points."""
        config = LoyaltyConfig.get_config()
        return config.calculate_points_value(self.points_balance)


class PointsTransaction(models.Model):
    """
    Points transaction history.
    """

    class Type(models.TextChoices):
        EARN = 'earn', _('Points Earned')
        REDEEM = 'redeem', _('Points Redeemed')
        BONUS = 'bonus', _('Bonus Points')
        ADJUST = 'adjust', _('Manual Adjustment')
        EXPIRE = 'expire', _('Points Expired')
        TIER_CHANGE = 'tier', _('Tier Change')
        RETURN = 'return', _('Return Deduction')

    # Transaction ID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    member = models.ForeignKey(
        LoyaltyMember,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Member')
    )
    transaction_type = models.CharField(
        _('Type'),
        max_length=20,
        choices=Type.choices
    )
    points = models.IntegerField(
        _('Points'),
        help_text=_('Positive for earned, negative for redeemed/expired')
    )
    balance_after = models.PositiveIntegerField(_('Balance After'))
    description = models.CharField(_('Description'), max_length=255, blank=True)

    # Reference to sale (optional)
    sale_id = models.PositiveIntegerField(_('Sale ID'), null=True, blank=True)

    # Reference to reward (optional)
    reward = models.ForeignKey(
        'Reward',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name=_('Reward')
    )

    # Processing info
    processed_by = models.CharField(_('Processed By'), max_length=255, blank=True)
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'loyalty'
        db_table = 'loyalty_transaction'
        verbose_name = _('Points Transaction')
        verbose_name_plural = _('Points Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member', '-created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['sale_id']),
        ]

    def __str__(self):
        sign = '+' if self.points > 0 else ''
        return f'{self.member.name}: {sign}{self.points} ({self.get_transaction_type_display()})'


class Reward(models.Model):
    """
    Redeemable rewards.
    """

    class RewardType(models.TextChoices):
        DISCOUNT_PERCENT = 'discount_percent', _('Discount %')
        DISCOUNT_AMOUNT = 'discount_amount', _('Discount Amount')
        FREE_PRODUCT = 'free_product', _('Free Product')
        FREE_SHIPPING = 'free_shipping', _('Free Shipping')
        GIFT_CARD = 'gift_card', _('Gift Card')

    name = models.CharField(_('Name'), max_length=100)
    name_es = models.CharField(_('Name (Spanish)'), max_length=100, blank=True)
    description = models.TextField(_('Description'), blank=True)

    # Visual
    icon = models.CharField(_('Icon'), max_length=50, default='gift-outline')
    image = models.ImageField(
        _('Image'),
        upload_to='loyalty/rewards/',
        blank=True,
        null=True
    )

    # Cost
    points_cost = models.PositiveIntegerField(
        _('Points Cost'),
        help_text=_('Points required to redeem')
    )

    # Reward value
    reward_type = models.CharField(
        _('Reward Type'),
        max_length=20,
        choices=RewardType.choices,
        default=RewardType.DISCOUNT_AMOUNT
    )
    value = models.DecimalField(
        _('Value'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Discount % or amount, or product value')
    )
    product_id = models.PositiveIntegerField(
        _('Product ID'),
        null=True,
        blank=True,
        help_text=_('For free product rewards')
    )
    product_name = models.CharField(
        _('Product Name'),
        max_length=255,
        blank=True
    )

    # Availability
    min_tier = models.ForeignKey(
        LoyaltyTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='available_rewards',
        verbose_name=_('Minimum Tier'),
        help_text=_('Minimum tier required to redeem')
    )
    valid_from = models.DateTimeField(_('Valid From'), null=True, blank=True)
    valid_until = models.DateTimeField(_('Valid Until'), null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(
        _('Max Redemptions'),
        null=True,
        blank=True,
        help_text=_('Total times this can be redeemed (null = unlimited)')
    )
    max_per_member = models.PositiveIntegerField(
        _('Max Per Member'),
        default=1,
        help_text=_('Times each member can redeem')
    )

    # Tracking
    times_redeemed = models.PositiveIntegerField(_('Times Redeemed'), default=0)
    order = models.PositiveIntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    is_featured = models.BooleanField(_('Featured'), default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'loyalty'
        db_table = 'loyalty_reward'
        verbose_name = _('Reward')
        verbose_name_plural = _('Rewards')
        ordering = ['order', '-is_featured', 'points_cost']

    def __str__(self):
        return f'{self.name} ({self.points_cost} pts)'

    def get_display_name(self, language='en'):
        """Get localized name."""
        if language == 'es' and self.name_es:
            return self.name_es
        return self.name

    def is_available(self):
        """Check if reward is currently available."""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_redemptions and self.times_redeemed >= self.max_redemptions:
            return False
        return True

    def can_redeem(self, member):
        """Check if member can redeem this reward."""
        if not self.is_available():
            return False, _('Reward not available')

        if member.points_balance < self.points_cost:
            return False, _('Insufficient points')

        if self.min_tier:
            if not member.tier or member.tier.min_points < self.min_tier.min_points:
                return False, _('Tier requirement not met')

        # Check per-member limit
        member_redemptions = PointsTransaction.objects.filter(
            member=member,
            reward=self,
            transaction_type=PointsTransaction.Type.REDEEM
        ).count()
        if member_redemptions >= self.max_per_member:
            return False, _('Maximum redemptions reached')

        return True, None


class RewardRedemption(models.Model):
    """
    Record of reward redemptions.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPLIED = 'applied', _('Applied')
        EXPIRED = 'expired', _('Expired')
        CANCELLED = 'cancelled', _('Cancelled')

    # Redemption identification
    code = models.CharField(
        _('Redemption Code'),
        max_length=20,
        unique=True
    )
    member = models.ForeignKey(
        LoyaltyMember,
        on_delete=models.CASCADE,
        related_name='redemptions',
        verbose_name=_('Member')
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.PROTECT,
        related_name='redemptions',
        verbose_name=_('Reward')
    )
    points_used = models.PositiveIntegerField(_('Points Used'))
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Value at time of redemption (for audit)
    reward_type = models.CharField(_('Reward Type'), max_length=20)
    reward_value = models.DecimalField(
        _('Reward Value'),
        max_digits=10,
        decimal_places=2
    )

    # Usage
    used_at = models.DateTimeField(_('Used At'), null=True, blank=True)
    sale_id = models.PositiveIntegerField(_('Applied to Sale'), null=True, blank=True)
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'loyalty'
        db_table = 'loyalty_redemption'
        verbose_name = _('Reward Redemption')
        verbose_name_plural = _('Reward Redemptions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['member', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.code} - {self.reward.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    def _generate_code(self):
        """Generate unique redemption code."""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not RewardRedemption.objects.filter(code=code).exists():
                return code

    def apply(self, sale_id):
        """Mark redemption as applied to a sale."""
        self.status = self.Status.APPLIED
        self.used_at = timezone.now()
        self.sale_id = sale_id
        self.save()
