from django.contrib import admin
from .models import LoyaltyConfig, LoyaltyTier, LoyaltyMember, PointsTransaction, Reward, RewardRedemption


@admin.register(LoyaltyConfig)
class LoyaltyConfigAdmin(admin.ModelAdmin):
    list_display = ['program_name', 'program_enabled', 'points_per_currency', 'points_value', 'auto_enroll']
    fieldsets = (
        ('Program Settings', {
            'fields': ('program_name', 'program_enabled')
        }),
        ('Points Configuration', {
            'fields': ('points_per_currency', 'points_value', 'minimum_redemption')
        }),
        ('Expiry Settings', {
            'fields': ('points_expire', 'expiry_months')
        }),
        ('Enrollment', {
            'fields': ('auto_enroll', 'welcome_points')
        }),
        ('Display', {
            'fields': ('show_points_on_receipt', 'show_available_rewards')
        }),
    )

    def has_add_permission(self, request):
        return not LoyaltyConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'min_points', 'min_spent', 'points_multiplier', 'discount_percent', 'is_default', 'is_active', 'order']
    list_filter = ['is_active', 'is_default']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'name_es']
    ordering = ['order', 'min_points']


@admin.register(LoyaltyMember)
class LoyaltyMemberAdmin(admin.ModelAdmin):
    list_display = ['member_number', 'name', 'email', 'tier', 'points_balance', 'lifetime_points', 'total_spent', 'is_active']
    list_filter = ['tier', 'is_active', 'enrolled_at']
    search_fields = ['member_number', 'card_number', 'name', 'email', 'phone']
    readonly_fields = ['member_number', 'lifetime_points', 'enrolled_at', 'last_activity_at', 'created_at', 'updated_at']
    raw_id_fields = ['tier']
    date_hierarchy = 'enrolled_at'


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'member', 'transaction_type', 'points', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['member__name', 'member__member_number', 'description']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['member', 'reward']
    date_hierarchy = 'created_at'


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'reward_type', 'points_cost', 'value', 'times_redeemed', 'is_active', 'is_featured', 'order']
    list_filter = ['reward_type', 'is_active', 'is_featured', 'min_tier']
    list_editable = ['is_active', 'is_featured', 'order']
    search_fields = ['name', 'name_es', 'description']
    raw_id_fields = ['min_tier']
    ordering = ['order', '-is_featured', 'points_cost']


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ['code', 'member', 'reward', 'points_used', 'status', 'created_at', 'used_at']
    list_filter = ['status', 'created_at', 'used_at']
    search_fields = ['code', 'member__name', 'member__member_number', 'reward__name']
    readonly_fields = ['code', 'created_at']
    raw_id_fields = ['member', 'reward']
    date_hierarchy = 'created_at'
