from django.contrib import admin
from .models import LoyaltySettings, LoyaltyTier, LoyaltyMember, PointsTransaction, Reward, RewardRedemption


@admin.register(LoyaltySettings)
class LoyaltySettingsAdmin(admin.ModelAdmin):
    list_display = ['program_name', 'program_enabled', 'points_per_currency', 'auto_enroll']


@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'min_points', 'points_multiplier', 'is_active']
    list_filter = ['is_active']


@admin.register(LoyaltyMember)
class LoyaltyMemberAdmin(admin.ModelAdmin):
    list_display = ['member_number', 'name', 'email', 'tier', 'points_balance', 'is_active']
    list_filter = ['tier', 'is_active']
    search_fields = ['member_number', 'name', 'email']


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ['member', 'transaction_type', 'points', 'created_at']
    list_filter = ['transaction_type']


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'reward_type', 'points_cost', 'is_active']
    list_filter = ['reward_type', 'is_active']


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ['code', 'member', 'reward', 'status', 'created_at']
    list_filter = ['status']
