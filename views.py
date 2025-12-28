"""
Loyalty Module Views
Member management, points, tiers, and rewards.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import csv

from apps.core.htmx import htmx_view

from .models import (
    LoyaltyConfig,
    LoyaltyTier,
    LoyaltyMember,
    PointsTransaction,
    Reward,
    RewardRedemption,
)


# =============================================================================
# Dashboard
# =============================================================================

@htmx_view(
    'loyalty/pages/index.html',
    'loyalty/partials/dashboard_content.html'
)
def dashboard(request):
    """Loyalty program dashboard with statistics."""
    config = LoyaltyConfig.get_config()

    # Statistics
    total_members = LoyaltyMember.objects.filter(is_active=True).count()
    total_points_issued = PointsTransaction.objects.filter(
        transaction_type=PointsTransaction.Type.EARN
    ).aggregate(total=Sum('points'))['total'] or 0
    total_points_redeemed = PointsTransaction.objects.filter(
        transaction_type=PointsTransaction.Type.REDEEM
    ).aggregate(total=Sum('points'))['total'] or 0
    active_rewards = Reward.objects.filter(is_active=True).count()

    # Recent activity
    recent_transactions = PointsTransaction.objects.select_related(
        'member', 'reward'
    ).order_by('-created_at')[:10]

    # Top members
    top_members = LoyaltyMember.objects.filter(
        is_active=True
    ).order_by('-lifetime_points')[:5]

    # Tier distribution
    tier_stats = LoyaltyMember.objects.filter(
        is_active=True
    ).values('tier__name', 'tier__color').annotate(
        count=Count('id')
    ).order_by('-count')

    context = {
        'config': config,
        'total_members': total_members,
        'total_points_issued': total_points_issued,
        'total_points_redeemed': abs(total_points_redeemed),
        'points_in_circulation': total_points_issued + total_points_redeemed,
        'active_rewards': active_rewards,
        'recent_transactions': recent_transactions,
        'top_members': top_members,
        'tier_stats': tier_stats,
    }
    return context


# =============================================================================
# Members
# =============================================================================

@htmx_view(
    'loyalty/pages/members.html',
    'loyalty/partials/members_list.html'
)
def members_list(request):
    """List loyalty members with search and pagination."""
    search = request.GET.get('search', '')
    tier_filter = request.GET.get('tier', '')
    status_filter = request.GET.get('status', 'active')
    page = request.GET.get('page', 1)

    members = LoyaltyMember.objects.select_related('tier')

    # Filters
    if search:
        members = members.filter(
            Q(member_number__icontains=search) |
            Q(card_number__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    if tier_filter:
        members = members.filter(tier_id=tier_filter)

    if status_filter == 'active':
        members = members.filter(is_active=True)
    elif status_filter == 'inactive':
        members = members.filter(is_active=False)

    members = members.order_by('-enrolled_at')

    # Pagination
    paginator = Paginator(members, 20)
    page_obj = paginator.get_page(page)

    tiers = LoyaltyTier.objects.filter(is_active=True)

    context = {
        'members': page_obj,
        'page_obj': page_obj,
        'search': search,
        'tier_filter': tier_filter,
        'status_filter': status_filter,
        'tiers': tiers,
        'total_count': paginator.count,
    }
    return context


@htmx_view(
    'loyalty/pages/member_form.html',
    'loyalty/partials/member_form.html'
)
def member_create(request):
    """Create a new loyalty member."""
    tiers = LoyaltyTier.objects.filter(is_active=True).order_by('order')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        card_number = request.POST.get('card_number', '').strip() or None
        tier_id = request.POST.get('tier') or None
        notes = request.POST.get('notes', '').strip()

        if not name:
            messages.error(request, _('Name is required'))
            return {'tiers': tiers, 'form_data': request.POST}

        # Check for duplicate card number
        if card_number and LoyaltyMember.objects.filter(card_number=card_number).exists():
            messages.error(request, _('Card number already exists'))
            return {'tiers': tiers, 'form_data': request.POST}

        member = LoyaltyMember.objects.create(
            name=name,
            email=email,
            phone=phone,
            card_number=card_number,
            tier_id=tier_id,
            notes=notes,
        )

        # Add welcome points
        config = LoyaltyConfig.get_config()
        if config.welcome_points > 0:
            member.add_points(
                config.welcome_points,
                description=_('Welcome bonus')
            )

        messages.success(request, _('Member created successfully'))
        return redirect('loyalty:member_detail', pk=member.pk)

    context = {
        'tiers': tiers,
        'form_data': {},
        'is_create': True,
    }
    return context


@htmx_view(
    'loyalty/pages/member_detail.html',
    'loyalty/partials/member_detail.html'
)
def member_detail(request, pk):
    """View member details and transaction history."""
    member = get_object_or_404(LoyaltyMember.objects.select_related('tier'), pk=pk)

    # Transaction history
    transactions = member.transactions.select_related('reward').order_by('-created_at')[:50]

    # Redemptions
    redemptions = member.redemptions.select_related('reward').order_by('-created_at')[:10]

    # Available rewards
    config = LoyaltyConfig.get_config()
    available_rewards = []
    for reward in Reward.objects.filter(is_active=True):
        can_redeem, reason = reward.can_redeem(member)
        available_rewards.append({
            'reward': reward,
            'can_redeem': can_redeem,
            'reason': reason,
        })

    context = {
        'member': member,
        'transactions': transactions,
        'redemptions': redemptions,
        'available_rewards': available_rewards,
        'config': config,
    }
    return context


@htmx_view(
    'loyalty/pages/member_form.html',
    'loyalty/partials/member_form.html'
)
def member_edit(request, pk):
    """Edit loyalty member."""
    member = get_object_or_404(LoyaltyMember, pk=pk)
    tiers = LoyaltyTier.objects.filter(is_active=True).order_by('order')

    if request.method == 'POST':
        member.name = request.POST.get('name', '').strip()
        member.email = request.POST.get('email', '').strip()
        member.phone = request.POST.get('phone', '').strip()
        card_number = request.POST.get('card_number', '').strip() or None
        member.tier_id = request.POST.get('tier') or None
        member.notes = request.POST.get('notes', '').strip()
        member.is_active = request.POST.get('is_active') == 'on'

        if not member.name:
            messages.error(request, _('Name is required'))
            return {'member': member, 'tiers': tiers, 'is_create': False}

        # Check for duplicate card number
        if card_number and LoyaltyMember.objects.filter(card_number=card_number).exclude(pk=pk).exists():
            messages.error(request, _('Card number already exists'))
            return {'member': member, 'tiers': tiers, 'is_create': False}

        member.card_number = card_number
        member.save()

        messages.success(request, _('Member updated successfully'))
        return redirect('loyalty:member_detail', pk=member.pk)

    context = {
        'member': member,
        'tiers': tiers,
        'is_create': False,
    }
    return context


@require_POST
def member_delete(request, pk):
    """Delete (deactivate) a loyalty member."""
    member = get_object_or_404(LoyaltyMember, pk=pk)
    member.is_active = False
    member.save()
    messages.success(request, _('Member deactivated'))
    return redirect('loyalty:members_list')


@htmx_view(
    'loyalty/pages/member_add_points.html',
    'loyalty/partials/member_add_points.html'
)
def member_add_points(request, pk):
    """Manually add bonus points to a member."""
    member = get_object_or_404(LoyaltyMember, pk=pk)

    if request.method == 'POST':
        try:
            points = int(request.POST.get('points', 0))
            description = request.POST.get('description', '').strip()

            if points <= 0:
                messages.error(request, _('Points must be positive'))
                return {'member': member}

            member.add_points(points, description=description or _('Manual adjustment'))
            messages.success(request, _('%(points)s points added') % {'points': points})
            return redirect('loyalty:member_detail', pk=member.pk)

        except ValueError:
            messages.error(request, _('Invalid points value'))
            return {'member': member}

    return {'member': member}


@htmx_view(
    'loyalty/pages/member_redeem.html',
    'loyalty/partials/member_redeem.html'
)
def member_redeem(request, pk):
    """Redeem a reward for a member."""
    member = get_object_or_404(LoyaltyMember, pk=pk)

    # Available rewards
    available_rewards = []
    for reward in Reward.objects.filter(is_active=True).order_by('points_cost'):
        can_redeem, reason = reward.can_redeem(member)
        available_rewards.append({
            'reward': reward,
            'can_redeem': can_redeem,
            'reason': reason,
        })

    if request.method == 'POST':
        reward_id = request.POST.get('reward_id')
        reward = get_object_or_404(Reward, pk=reward_id)

        can_redeem, reason = reward.can_redeem(member)
        if not can_redeem:
            messages.error(request, reason)
            return {'member': member, 'available_rewards': available_rewards}

        # Create redemption
        redemption = RewardRedemption.objects.create(
            member=member,
            reward=reward,
            points_used=reward.points_cost,
            reward_type=reward.reward_type,
            reward_value=reward.value,
        )

        # Deduct points
        member.redeem_points(
            reward.points_cost,
            description=f'Reward: {reward.name}',
        )

        # Update reward stats
        reward.times_redeemed += 1
        reward.save()

        messages.success(request, _('Reward redeemed! Code: %(code)s') % {'code': redemption.code})
        return redirect('loyalty:member_detail', pk=member.pk)

    return {'member': member, 'available_rewards': available_rewards}


def export_members_csv(request):
    """Export members to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="loyalty_members.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Member Number', 'Card Number', 'Name', 'Email', 'Phone',
        'Tier', 'Points Balance', 'Lifetime Points', 'Total Spent',
        'Visit Count', 'Enrolled At', 'Last Activity', 'Status'
    ])

    members = LoyaltyMember.objects.select_related('tier').order_by('-enrolled_at')
    for member in members:
        writer.writerow([
            member.member_number,
            member.card_number or '',
            member.name,
            member.email,
            member.phone,
            member.tier.name if member.tier else '',
            member.points_balance,
            member.lifetime_points,
            member.total_spent,
            member.visit_count,
            member.enrolled_at.strftime('%Y-%m-%d %H:%M') if member.enrolled_at else '',
            member.last_activity_at.strftime('%Y-%m-%d %H:%M') if member.last_activity_at else '',
            'Active' if member.is_active else 'Inactive',
        ])

    return response


# =============================================================================
# Tiers
# =============================================================================

@htmx_view(
    'loyalty/pages/tiers.html',
    'loyalty/partials/tiers_list.html'
)
def tiers_list(request):
    """List loyalty tiers."""
    tiers = LoyaltyTier.objects.annotate(
        member_count=Count('members', filter=Q(members__is_active=True))
    ).order_by('order', 'min_points')

    return {'tiers': tiers}


@htmx_view(
    'loyalty/pages/tier_form.html',
    'loyalty/partials/tier_form.html'
)
def tier_create(request):
    """Create a new tier."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        name_es = request.POST.get('name_es', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon', 'star-outline').strip()
        color = request.POST.get('color', '#cd7f32').strip()
        min_points = int(request.POST.get('min_points', 0))
        min_spent = Decimal(request.POST.get('min_spent', '0'))
        points_multiplier = Decimal(request.POST.get('points_multiplier', '1.00'))
        discount_percent = Decimal(request.POST.get('discount_percent', '0'))
        free_shipping = request.POST.get('free_shipping') == 'on'
        exclusive_offers = request.POST.get('exclusive_offers') == 'on'
        order = int(request.POST.get('order', 0))
        is_default = request.POST.get('is_default') == 'on'

        if not name:
            messages.error(request, _('Name is required'))
            return {'form_data': request.POST, 'is_create': True}

        LoyaltyTier.objects.create(
            name=name,
            name_es=name_es,
            description=description,
            icon=icon,
            color=color,
            min_points=min_points,
            min_spent=min_spent,
            points_multiplier=points_multiplier,
            discount_percent=discount_percent,
            free_shipping=free_shipping,
            exclusive_offers=exclusive_offers,
            order=order,
            is_default=is_default,
        )

        messages.success(request, _('Tier created successfully'))
        return redirect('loyalty:tiers_list')

    return {'form_data': {}, 'is_create': True}


@htmx_view(
    'loyalty/pages/tier_form.html',
    'loyalty/partials/tier_form.html'
)
def tier_edit(request, pk):
    """Edit a tier."""
    tier = get_object_or_404(LoyaltyTier, pk=pk)

    if request.method == 'POST':
        tier.name = request.POST.get('name', '').strip()
        tier.name_es = request.POST.get('name_es', '').strip()
        tier.description = request.POST.get('description', '').strip()
        tier.icon = request.POST.get('icon', 'star-outline').strip()
        tier.color = request.POST.get('color', '#cd7f32').strip()
        tier.min_points = int(request.POST.get('min_points', 0))
        tier.min_spent = Decimal(request.POST.get('min_spent', '0'))
        tier.points_multiplier = Decimal(request.POST.get('points_multiplier', '1.00'))
        tier.discount_percent = Decimal(request.POST.get('discount_percent', '0'))
        tier.free_shipping = request.POST.get('free_shipping') == 'on'
        tier.exclusive_offers = request.POST.get('exclusive_offers') == 'on'
        tier.order = int(request.POST.get('order', 0))
        tier.is_default = request.POST.get('is_default') == 'on'
        tier.is_active = request.POST.get('is_active') == 'on'

        if not tier.name:
            messages.error(request, _('Name is required'))
            return {'tier': tier, 'is_create': False}

        tier.save()
        messages.success(request, _('Tier updated successfully'))
        return redirect('loyalty:tiers_list')

    return {'tier': tier, 'is_create': False}


@require_POST
def tier_delete(request, pk):
    """Delete a tier."""
    tier = get_object_or_404(LoyaltyTier, pk=pk)

    # Check for members in this tier
    member_count = tier.members.filter(is_active=True).count()
    if member_count > 0:
        messages.error(request, _('Cannot delete tier with %(count)s active members') % {'count': member_count})
        return redirect('loyalty:tiers_list')

    tier.delete()
    messages.success(request, _('Tier deleted'))
    return redirect('loyalty:tiers_list')


# =============================================================================
# Rewards
# =============================================================================

@htmx_view(
    'loyalty/pages/rewards.html',
    'loyalty/partials/rewards_list.html'
)
def rewards_list(request):
    """List rewards."""
    status = request.GET.get('status', 'active')

    rewards = Reward.objects.all()
    if status == 'active':
        rewards = rewards.filter(is_active=True)
    elif status == 'inactive':
        rewards = rewards.filter(is_active=False)

    rewards = rewards.order_by('order', '-is_featured', 'points_cost')

    return {'rewards': rewards, 'status': status}


@htmx_view(
    'loyalty/pages/reward_form.html',
    'loyalty/partials/reward_form.html'
)
def reward_create(request):
    """Create a new reward."""
    tiers = LoyaltyTier.objects.filter(is_active=True).order_by('order')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        name_es = request.POST.get('name_es', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon', 'gift-outline').strip()
        points_cost = int(request.POST.get('points_cost', 0))
        reward_type = request.POST.get('reward_type', Reward.RewardType.DISCOUNT_AMOUNT)
        value = Decimal(request.POST.get('value', '0'))
        product_id = request.POST.get('product_id') or None
        product_name = request.POST.get('product_name', '').strip()
        min_tier_id = request.POST.get('min_tier') or None
        max_redemptions = request.POST.get('max_redemptions') or None
        max_per_member = int(request.POST.get('max_per_member', 1))
        order = int(request.POST.get('order', 0))
        is_featured = request.POST.get('is_featured') == 'on'

        if not name:
            messages.error(request, _('Name is required'))
            return {'form_data': request.POST, 'tiers': tiers, 'is_create': True}

        if points_cost <= 0:
            messages.error(request, _('Points cost must be positive'))
            return {'form_data': request.POST, 'tiers': tiers, 'is_create': True}

        reward = Reward.objects.create(
            name=name,
            name_es=name_es,
            description=description,
            icon=icon,
            points_cost=points_cost,
            reward_type=reward_type,
            value=value,
            product_id=product_id,
            product_name=product_name,
            min_tier_id=min_tier_id,
            max_redemptions=int(max_redemptions) if max_redemptions else None,
            max_per_member=max_per_member,
            order=order,
            is_featured=is_featured,
        )

        # Handle image upload
        if 'image' in request.FILES:
            reward.image = request.FILES['image']
            reward.save()

        messages.success(request, _('Reward created successfully'))
        return redirect('loyalty:rewards_list')

    return {
        'form_data': {},
        'tiers': tiers,
        'is_create': True,
        'reward_types': Reward.RewardType.choices,
    }


@htmx_view(
    'loyalty/pages/reward_detail.html',
    'loyalty/partials/reward_detail.html'
)
def reward_detail(request, pk):
    """View reward details."""
    reward = get_object_or_404(Reward.objects.select_related('min_tier'), pk=pk)

    # Recent redemptions
    redemptions = RewardRedemption.objects.filter(
        reward=reward
    ).select_related('member').order_by('-created_at')[:20]

    return {
        'reward': reward,
        'redemptions': redemptions,
    }


@htmx_view(
    'loyalty/pages/reward_form.html',
    'loyalty/partials/reward_form.html'
)
def reward_edit(request, pk):
    """Edit a reward."""
    reward = get_object_or_404(Reward, pk=pk)
    tiers = LoyaltyTier.objects.filter(is_active=True).order_by('order')

    if request.method == 'POST':
        reward.name = request.POST.get('name', '').strip()
        reward.name_es = request.POST.get('name_es', '').strip()
        reward.description = request.POST.get('description', '').strip()
        reward.icon = request.POST.get('icon', 'gift-outline').strip()
        reward.points_cost = int(request.POST.get('points_cost', 0))
        reward.reward_type = request.POST.get('reward_type', Reward.RewardType.DISCOUNT_AMOUNT)
        reward.value = Decimal(request.POST.get('value', '0'))
        reward.product_id = request.POST.get('product_id') or None
        reward.product_name = request.POST.get('product_name', '').strip()
        reward.min_tier_id = request.POST.get('min_tier') or None
        max_redemptions = request.POST.get('max_redemptions')
        reward.max_redemptions = int(max_redemptions) if max_redemptions else None
        reward.max_per_member = int(request.POST.get('max_per_member', 1))
        reward.order = int(request.POST.get('order', 0))
        reward.is_featured = request.POST.get('is_featured') == 'on'
        reward.is_active = request.POST.get('is_active') == 'on'

        if not reward.name:
            messages.error(request, _('Name is required'))
            return {'reward': reward, 'tiers': tiers, 'is_create': False}

        if reward.points_cost <= 0:
            messages.error(request, _('Points cost must be positive'))
            return {'reward': reward, 'tiers': tiers, 'is_create': False}

        # Handle image upload
        if 'image' in request.FILES:
            reward.image = request.FILES['image']

        reward.save()
        messages.success(request, _('Reward updated successfully'))
        return redirect('loyalty:reward_detail', pk=reward.pk)

    return {
        'reward': reward,
        'tiers': tiers,
        'is_create': False,
        'reward_types': Reward.RewardType.choices,
    }


@require_POST
def reward_delete(request, pk):
    """Delete a reward (soft delete - deactivate)."""
    reward = get_object_or_404(Reward, pk=pk)
    reward.is_active = False
    reward.save()
    messages.success(request, _('Reward deactivated'))
    return redirect('loyalty:rewards_list')


# =============================================================================
# Transactions
# =============================================================================

@htmx_view(
    'loyalty/pages/transactions.html',
    'loyalty/partials/transactions_list.html'
)
def transactions_list(request):
    """List all point transactions."""
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    page = request.GET.get('page', 1)

    transactions = PointsTransaction.objects.select_related('member', 'reward')

    if search:
        transactions = transactions.filter(
            Q(member__name__icontains=search) |
            Q(member__member_number__icontains=search) |
            Q(description__icontains=search)
        )

    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    transactions = transactions.order_by('-created_at')

    # Pagination
    paginator = Paginator(transactions, 50)
    page_obj = paginator.get_page(page)

    return {
        'transactions': page_obj,
        'page_obj': page_obj,
        'search': search,
        'type_filter': type_filter,
        'transaction_types': PointsTransaction.Type.choices,
    }


# =============================================================================
# Settings
# =============================================================================

@htmx_view(
    'loyalty/pages/settings.html',
    'loyalty/partials/settings_form.html'
)
def settings_view(request):
    """Loyalty program settings."""
    config = LoyaltyConfig.get_config()

    if request.method == 'POST':
        config.program_name = request.POST.get('program_name', 'Loyalty Program').strip()
        config.program_enabled = request.POST.get('program_enabled') == 'on'
        config.points_per_currency = Decimal(request.POST.get('points_per_currency', '1.00'))
        config.points_value = Decimal(request.POST.get('points_value', '0.01'))
        config.minimum_redemption = int(request.POST.get('minimum_redemption', 100))
        config.points_expire = request.POST.get('points_expire') == 'on'
        config.expiry_months = int(request.POST.get('expiry_months', 12))
        config.auto_enroll = request.POST.get('auto_enroll') == 'on'
        config.welcome_points = int(request.POST.get('welcome_points', 0))
        config.show_points_on_receipt = request.POST.get('show_points_on_receipt') == 'on'
        config.show_available_rewards = request.POST.get('show_available_rewards') == 'on'
        config.save()

        messages.success(request, _('Settings saved'))
        return redirect('loyalty:settings')

    return {'config': config}


# =============================================================================
# API Endpoints (for POS integration)
# =============================================================================

@require_GET
def api_member_search(request):
    """Search for members by card number, phone, or member number."""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'members': []})

    members = LoyaltyMember.objects.filter(
        is_active=True
    ).filter(
        Q(member_number__icontains=query) |
        Q(card_number__icontains=query) |
        Q(phone__icontains=query) |
        Q(name__icontains=query)
    ).select_related('tier')[:10]

    results = [{
        'id': m.id,
        'member_number': m.member_number,
        'card_number': m.card_number,
        'name': m.name,
        'phone': m.phone,
        'tier': m.tier.name if m.tier else None,
        'tier_color': m.tier.color if m.tier else None,
        'points_balance': m.points_balance,
        'discount_percent': float(m.tier.discount_percent) if m.tier else 0,
    } for m in members]

    return JsonResponse({'members': results})


@require_GET
def api_member_balance(request, pk):
    """Get member's current balance and tier info."""
    member = get_object_or_404(LoyaltyMember.objects.select_related('tier'), pk=pk, is_active=True)
    config = LoyaltyConfig.get_config()

    return JsonResponse({
        'id': member.id,
        'member_number': member.member_number,
        'name': member.name,
        'points_balance': member.points_balance,
        'points_value': float(config.calculate_points_value(member.points_balance)),
        'tier': {
            'name': member.tier.name if member.tier else None,
            'color': member.tier.color if member.tier else None,
            'discount_percent': float(member.tier.discount_percent) if member.tier else 0,
            'points_multiplier': float(member.tier.points_multiplier) if member.tier else 1,
        } if member.tier else None,
    })


@require_GET
def api_available_rewards(request, member_id):
    """Get available rewards for a member."""
    member = get_object_or_404(LoyaltyMember, pk=member_id, is_active=True)

    rewards = Reward.objects.filter(is_active=True).order_by('points_cost')
    results = []

    for reward in rewards:
        can_redeem, reason = reward.can_redeem(member)
        results.append({
            'id': reward.id,
            'name': reward.name,
            'points_cost': reward.points_cost,
            'reward_type': reward.reward_type,
            'value': float(reward.value),
            'can_redeem': can_redeem,
            'reason': str(reason) if reason else None,
        })

    return JsonResponse({'rewards': results})
