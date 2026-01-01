from django.urls import path
from . import views

app_name = 'loyalty'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Members
    path('members/', views.members_list, name='members_list'),
    path('members/create/', views.member_create, name='member_create'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),
    path('members/<int:pk>/add-points/', views.member_add_points, name='member_add_points'),
    path('members/<int:pk>/redeem/', views.member_redeem, name='member_redeem'),
    path('members/export/csv/', views.export_members_csv, name='export_members_csv'),

    # Tiers
    path('tiers/', views.tiers_list, name='tiers_list'),
    path('tiers/create/', views.tier_create, name='tier_create'),
    path('tiers/<int:pk>/edit/', views.tier_edit, name='tier_edit'),
    path('tiers/<int:pk>/delete/', views.tier_delete, name='tier_delete'),

    # Rewards
    path('rewards/', views.rewards_list, name='rewards_list'),
    path('rewards/create/', views.reward_create, name='reward_create'),
    path('rewards/<int:pk>/', views.reward_detail, name='reward_detail'),
    path('rewards/<int:pk>/edit/', views.reward_edit, name='reward_edit'),
    path('rewards/<int:pk>/delete/', views.reward_delete, name='reward_delete'),

    # Transactions
    path('transactions/', views.transactions_list, name='transactions_list'),

    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),
    path('settings/toggle/', views.settings_toggle, name='settings_toggle'),
    path('settings/reset/', views.settings_reset, name='settings_reset'),

    # API endpoints (for POS integration)
    path('api/search/', views.api_member_search, name='api_member_search'),
    path('api/members/<int:pk>/balance/', views.api_member_balance, name='api_member_balance'),
    path('api/rewards/available/<int:member_id>/', views.api_available_rewards, name='api_available_rewards'),
]
