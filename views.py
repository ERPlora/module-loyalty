"""
Loyalty Module Views
Member management, points, tiers, and rewards.
"""

import json
import csv

from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from decimal import Decimal

from apps.accounts.decorators import login_required, permission_required
from apps.core.htmx import htmx_view
from apps.modules_runtime.navigation import with_module_nav

from .models import (
    LoyaltySettings,
    LoyaltyTier,
    LoyaltyMember,
    PointsTransaction,
    Reward,
    RewardRedemption,
)
from .forms import (
    LoyaltyMemberForm,
    LoyaltyTierForm,
    RewardForm,
    MemberFilterForm,
)


def _hub_id(request):
    return request.session.get('hub_id')


def _employee(request):
    from apps.accounts.models import LocalUser
    uid = request.session.get('local_user_id')
    if uid:
        return LocalUser.objects.filter(id=uid).first()
    return None


# =============================================================================
# Dashboard
# =============================================================================

@login_required
@with_module_nav('loyalty', 'dashboard')
@htmx_view('loyalty/pages/index.html', 'loyalty/partials/dashboard_content.html')
def dashboard(request):
    hub = _hub_id(request)
    settings = LoyaltySettings.get_settings(hub)

    members_qs = LoyaltyMember.objects.filter(hub_id=hub, is_deleted=False)
    transactions_qs = PointsTransaction.objects.filter(hub_id=hub, is_deleted=False)

    total_members = members_qs.filter(is_active=True).count()
    total_points_issued = transactions_qs.filter(
        transaction_type=PointsTransaction.Type.EARN,
    ).aggregate(total=Sum('points'))['total'] or 0
    total_points_redeemed = transactions_qs.filter(
        transaction_type=PointsTransaction.Type.REDEEM,
    ).aggregate(total=Sum('points'))['total'] or 0
    active_rewards = Reward.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).count()

    recent_transactions = transactions_qs.select_related(
        'member', 'reward',
    ).order_by('-created_at')[:10]

    top_members = members_qs.filter(
        is_active=True,
    ).order_by('-lifetime_points')[:5]

    tier_stats = members_qs.filter(
        is_active=True,
    ).values('tier__name', 'tier__color').annotate(
        count=Count('id'),
    ).order_by('-count')

    return {
        'settings': settings,
        'total_members': total_members,
        'total_points_issued': total_points_issued,
        'total_points_redeemed': abs(total_points_redeemed),
        'points_in_circulation': total_points_issued + total_points_redeemed,
        'active_rewards': active_rewards,
        'recent_transactions': recent_transactions,
        'top_members': top_members,
        'tier_stats': tier_stats,
    }


# =============================================================================
# Members
# =============================================================================

@login_required
@with_module_nav('loyalty', 'members')
@htmx_view('loyalty/pages/members.html', 'loyalty/partials/members_list.html')
def members_list(request):
    hub = _hub_id(request)
    filter_form = MemberFilterForm(request.GET)

    members = LoyaltyMember.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('tier')

    if filter_form.is_valid():
        q = filter_form.cleaned_data.get('q')
        tier = filter_form.cleaned_data.get('tier')
        status = filter_form.cleaned_data.get('status')

        if q:
            members = members.filter(
                Q(member_number__icontains=q) |
                Q(card_number__icontains=q) |
                Q(name__icontains=q) |
                Q(email__icontains=q) |
                Q(phone__icontains=q)
            )
        if tier:
            members = members.filter(tier_id=tier)
        if status == 'active':
            members = members.filter(is_active=True)
        elif status == 'inactive':
            members = members.filter(is_active=False)

    members = members.order_by('-enrolled_at')

    paginator = Paginator(members, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    tiers = LoyaltyTier.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    )

    return {
        'members': page_obj,
        'page_obj': page_obj,
        'filter_form': filter_form,
        'tiers': tiers,
        'total_count': paginator.count,
    }


@login_required
@with_module_nav('loyalty', 'members')
@htmx_view('loyalty/pages/member_form.html', 'loyalty/partials/member_form.html')
def member_create(request):
    hub = _hub_id(request)
    tiers = LoyaltyTier.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('sort_order')

    if request.method == 'POST':
        form = LoyaltyMemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.hub_id = hub
            member.save()

            # Welcome points
            settings = LoyaltySettings.get_settings(hub)
            if settings.welcome_points > 0:
                member.add_points(
                    settings.welcome_points,
                    description=str(_('Welcome bonus')),
                    employee=_employee(request),
                )

            messages.success(request, _('Member created successfully'))
            return redirect('loyalty:member_detail', pk=member.pk)
        return {'form': form, 'tiers': tiers, 'is_create': True}

    form = LoyaltyMemberForm()
    return {'form': form, 'tiers': tiers, 'is_create': True}


@login_required
@with_module_nav('loyalty', 'members')
@htmx_view('loyalty/pages/member_detail.html', 'loyalty/partials/member_detail.html')
def member_detail(request, pk):
    hub = _hub_id(request)
    member = get_object_or_404(
        LoyaltyMember.objects.select_related('tier'),
        pk=pk, hub_id=hub, is_deleted=False,
    )

    transactions = member.transactions.filter(
        is_deleted=False,
    ).select_related('reward').order_by('-created_at')[:50]

    redemptions = member.redemptions.filter(
        is_deleted=False,
    ).select_related('reward').order_by('-created_at')[:10]

    settings = LoyaltySettings.get_settings(hub)
    available_rewards = []
    for reward in Reward.objects.filter(hub_id=hub, is_deleted=False, is_active=True):
        can_redeem, reason = reward.can_redeem(member)
        available_rewards.append({
            'reward': reward,
            'can_redeem': can_redeem,
            'reason': reason,
        })

    return {
        'member': member,
        'transactions': transactions,
        'redemptions': redemptions,
        'available_rewards': available_rewards,
        'settings': settings,
    }


@login_required
@with_module_nav('loyalty', 'members')
@htmx_view('loyalty/pages/member_form.html', 'loyalty/partials/member_form.html')
def member_edit(request, pk):
    hub = _hub_id(request)
    member = get_object_or_404(
        LoyaltyMember, pk=pk, hub_id=hub, is_deleted=False,
    )
    tiers = LoyaltyTier.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('sort_order')

    if request.method == 'POST':
        form = LoyaltyMemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, _('Member updated successfully'))
            return redirect('loyalty:member_detail', pk=member.pk)
        return {'form': form, 'member': member, 'tiers': tiers, 'is_create': False}

    form = LoyaltyMemberForm(instance=member)
    return {'form': form, 'member': member, 'tiers': tiers, 'is_create': False}


@login_required
@require_POST
def member_delete(request, pk):
    hub = _hub_id(request)
    member = get_object_or_404(
        LoyaltyMember, pk=pk, hub_id=hub, is_deleted=False,
    )
    member.is_deleted = True
    member.deleted_at = timezone.now()
    member.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    messages.success(request, _('Member deleted'))
    return redirect('loyalty:members_list')


@login_required
@with_module_nav('loyalty', 'members')
@htmx_view('loyalty/pages/member_add_points.html', 'loyalty/partials/member_add_points.html')
def member_add_points(request, pk):
    hub = _hub_id(request)
    member = get_object_or_404(
        LoyaltyMember, pk=pk, hub_id=hub, is_deleted=False,
    )

    if request.method == 'POST':
        try:
            points = int(request.POST.get('points', 0))
            description = request.POST.get('description', '').strip()

            if points <= 0:
                messages.error(request, _('Points must be positive'))
                return {'member': member}

            member.add_points(
                points,
                description=description or str(_('Manual adjustment')),
                employee=_employee(request),
            )
            messages.success(request, _('%(points)s points added') % {'points': points})
            return redirect('loyalty:member_detail', pk=member.pk)
        except ValueError:
            messages.error(request, _('Invalid points value'))
            return {'member': member}

    return {'member': member}


@login_required
@with_module_nav('loyalty', 'members')
@htmx_view('loyalty/pages/member_redeem.html', 'loyalty/partials/member_redeem.html')
def member_redeem(request, pk):
    hub = _hub_id(request)
    member = get_object_or_404(
        LoyaltyMember, pk=pk, hub_id=hub, is_deleted=False,
    )

    available_rewards = []
    for reward in Reward.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('points_cost'):
        can_redeem, reason = reward.can_redeem(member)
        available_rewards.append({
            'reward': reward,
            'can_redeem': can_redeem,
            'reason': reason,
        })

    if request.method == 'POST':
        reward_id = request.POST.get('reward_id')
        reward = get_object_or_404(
            Reward, pk=reward_id, hub_id=hub, is_deleted=False,
        )

        can_redeem, reason = reward.can_redeem(member)
        if not can_redeem:
            messages.error(request, reason)
            return {'member': member, 'available_rewards': available_rewards}

        redemption = RewardRedemption.objects.create(
            hub_id=hub,
            member=member,
            reward=reward,
            points_used=reward.points_cost,
            reward_type=reward.reward_type,
            reward_value=reward.value,
        )

        member.redeem_points(
            reward.points_cost,
            description=f'Reward: {reward.name}',
            employee=_employee(request),
        )

        reward.times_redeemed += 1
        reward.save(update_fields=['times_redeemed', 'updated_at'])

        messages.success(request, _('Reward redeemed! Code: %(code)s') % {'code': redemption.code})
        return redirect('loyalty:member_detail', pk=member.pk)

    return {'member': member, 'available_rewards': available_rewards}


@login_required
def export_members_csv(request):
    hub = _hub_id(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="loyalty_members.csv"'

    writer = csv.writer(response)
    writer.writerow([
        gettext('Member Number'), gettext('Card Number'), gettext('Name'), gettext('Email'), gettext('Phone'),
        gettext('Tier'), gettext('Points Balance'), gettext('Lifetime Points'), gettext('Total Spent'),
        gettext('Visit Count'), gettext('Enrolled At'), gettext('Last Activity'), gettext('Status'),
    ])

    members = LoyaltyMember.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('tier').order_by('-enrolled_at')

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
            gettext('Active') if member.is_active else gettext('Inactive'),
        ])

    return response


# =============================================================================
# Tiers
# =============================================================================

@login_required
@with_module_nav('loyalty', 'tiers')
@htmx_view('loyalty/pages/tiers.html', 'loyalty/partials/tiers_list.html')
def tiers_list(request):
    hub = _hub_id(request)
    tiers = LoyaltyTier.objects.filter(
        hub_id=hub, is_deleted=False,
    ).annotate(
        member_count=Count(
            'members',
            filter=Q(members__is_active=True, members__is_deleted=False),
        ),
    ).order_by('sort_order', 'min_points')

    return {'tiers': tiers}


@login_required
@with_module_nav('loyalty', 'tiers')
@htmx_view('loyalty/pages/tier_form.html', 'loyalty/partials/tier_form.html')
def tier_create(request):
    hub = _hub_id(request)

    if request.method == 'POST':
        form = LoyaltyTierForm(request.POST)
        if form.is_valid():
            tier = form.save(commit=False)
            tier.hub_id = hub
            tier.save()
            messages.success(request, _('Tier created successfully'))
            return redirect('loyalty:tiers_list')
        return {'form': form, 'is_create': True}

    form = LoyaltyTierForm()
    return {'form': form, 'is_create': True}


@login_required
@with_module_nav('loyalty', 'tiers')
@htmx_view('loyalty/pages/tier_form.html', 'loyalty/partials/tier_form.html')
def tier_edit(request, pk):
    hub = _hub_id(request)
    tier = get_object_or_404(
        LoyaltyTier, pk=pk, hub_id=hub, is_deleted=False,
    )

    if request.method == 'POST':
        form = LoyaltyTierForm(request.POST, instance=tier)
        if form.is_valid():
            form.save()
            messages.success(request, _('Tier updated successfully'))
            return redirect('loyalty:tiers_list')
        return {'form': form, 'tier': tier, 'is_create': False}

    form = LoyaltyTierForm(instance=tier)
    return {'form': form, 'tier': tier, 'is_create': False}


@login_required
@require_POST
def tier_delete(request, pk):
    hub = _hub_id(request)
    tier = get_object_or_404(
        LoyaltyTier, pk=pk, hub_id=hub, is_deleted=False,
    )

    member_count = tier.members.filter(is_active=True, is_deleted=False).count()
    if member_count > 0:
        messages.error(
            request,
            _('Cannot delete tier with %(count)s active members') % {'count': member_count},
        )
        return redirect('loyalty:tiers_list')

    tier.is_deleted = True
    tier.deleted_at = timezone.now()
    tier.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    messages.success(request, _('Tier deleted'))
    return redirect('loyalty:tiers_list')


# =============================================================================
# Rewards
# =============================================================================

@login_required
@with_module_nav('loyalty', 'rewards')
@htmx_view('loyalty/pages/rewards.html', 'loyalty/partials/rewards_list.html')
def rewards_list(request):
    hub = _hub_id(request)
    status = request.GET.get('status', 'active')

    rewards = Reward.objects.filter(hub_id=hub, is_deleted=False)
    if status == 'active':
        rewards = rewards.filter(is_active=True)
    elif status == 'inactive':
        rewards = rewards.filter(is_active=False)

    rewards = rewards.order_by('sort_order', '-is_featured', 'points_cost')

    return {'rewards': rewards, 'status': status}


@login_required
@with_module_nav('loyalty', 'rewards')
@htmx_view('loyalty/pages/reward_form.html', 'loyalty/partials/reward_form.html')
def reward_create(request):
    hub = _hub_id(request)
    tiers = LoyaltyTier.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('sort_order')

    if request.method == 'POST':
        form = RewardForm(request.POST, request.FILES)
        if form.is_valid():
            reward = form.save(commit=False)
            reward.hub_id = hub
            reward.save()
            messages.success(request, _('Reward created successfully'))
            return redirect('loyalty:rewards_list')
        return {'form': form, 'tiers': tiers, 'is_create': True, 'reward_types': Reward.RewardType.choices}

    form = RewardForm()
    return {
        'form': form,
        'tiers': tiers,
        'is_create': True,
        'reward_types': Reward.RewardType.choices,
    }


@login_required
@with_module_nav('loyalty', 'rewards')
@htmx_view('loyalty/pages/reward_detail.html', 'loyalty/partials/reward_detail.html')
def reward_detail(request, pk):
    hub = _hub_id(request)
    reward = get_object_or_404(
        Reward.objects.select_related('min_tier'),
        pk=pk, hub_id=hub, is_deleted=False,
    )

    redemptions = RewardRedemption.objects.filter(
        hub_id=hub, reward=reward, is_deleted=False,
    ).select_related('member').order_by('-created_at')[:20]

    return {'reward': reward, 'redemptions': redemptions}


@login_required
@with_module_nav('loyalty', 'rewards')
@htmx_view('loyalty/pages/reward_form.html', 'loyalty/partials/reward_form.html')
def reward_edit(request, pk):
    hub = _hub_id(request)
    reward = get_object_or_404(
        Reward, pk=pk, hub_id=hub, is_deleted=False,
    )
    tiers = LoyaltyTier.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('sort_order')

    if request.method == 'POST':
        form = RewardForm(request.POST, request.FILES, instance=reward)
        if form.is_valid():
            form.save()
            messages.success(request, _('Reward updated successfully'))
            return redirect('loyalty:reward_detail', pk=reward.pk)
        return {'form': form, 'reward': reward, 'tiers': tiers, 'is_create': False, 'reward_types': Reward.RewardType.choices}

    form = RewardForm(instance=reward)
    return {
        'form': form,
        'reward': reward,
        'tiers': tiers,
        'is_create': False,
        'reward_types': Reward.RewardType.choices,
    }


@login_required
@require_POST
def reward_delete(request, pk):
    hub = _hub_id(request)
    reward = get_object_or_404(
        Reward, pk=pk, hub_id=hub, is_deleted=False,
    )
    reward.is_deleted = True
    reward.deleted_at = timezone.now()
    reward.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    messages.success(request, _('Reward deleted'))
    return redirect('loyalty:rewards_list')


# =============================================================================
# Transactions
# =============================================================================

@login_required
@with_module_nav('loyalty', 'transactions')
@htmx_view('loyalty/pages/transactions.html', 'loyalty/partials/transactions_list.html')
def transactions_list(request):
    hub = _hub_id(request)
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')

    transactions = PointsTransaction.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('member', 'reward')

    if search:
        transactions = transactions.filter(
            Q(member__name__icontains=search) |
            Q(member__member_number__icontains=search) |
            Q(description__icontains=search)
        )

    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    transactions = transactions.order_by('-created_at')

    paginator = Paginator(transactions, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

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

@login_required
@permission_required('loyalty.manage_settings')
@with_module_nav('loyalty', 'settings')
@htmx_view('loyalty/pages/settings.html', 'loyalty/partials/settings_form.html')
def settings_view(request):
    hub = _hub_id(request)
    settings = LoyaltySettings.get_settings(hub)
    return {'settings': settings}


@login_required
@permission_required('loyalty.manage_settings')
@require_POST
def settings_save(request):
    hub = _hub_id(request)
    try:
        data = json.loads(request.body)
        settings = LoyaltySettings.get_settings(hub)

        settings.program_name = data.get('program_name', 'Loyalty Program')
        settings.program_enabled = data.get('program_enabled', True)
        settings.points_per_currency = Decimal(str(data.get('points_per_currency', '1.00')))
        settings.points_value = Decimal(str(data.get('points_value', '0.01')))
        settings.minimum_redemption = int(data.get('minimum_redemption', 100))
        settings.points_expire = data.get('points_expire', False)
        settings.expiry_months = int(data.get('expiry_months', 12))
        settings.auto_enroll = data.get('auto_enroll', True)
        settings.welcome_points = int(data.get('welcome_points', 0))
        settings.show_points_on_receipt = data.get('show_points_on_receipt', True)
        settings.show_available_rewards = data.get('show_available_rewards', True)

        settings.save()
        return JsonResponse({'success': True, 'message': str(_('Settings saved'))})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': str(_('Invalid JSON'))}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@permission_required('loyalty.manage_settings')
@require_POST
def settings_toggle(request):
    hub = _hub_id(request)
    name = request.POST.get('name') or request.POST.get('setting_name')
    value = request.POST.get('value', request.POST.get('setting_value', 'false'))
    setting_value = value == 'true' or value is True

    settings = LoyaltySettings.get_settings(hub)

    boolean_settings = [
        'program_enabled', 'points_expire', 'auto_enroll',
        'show_points_on_receipt', 'show_available_rewards',
    ]

    if not name or name not in boolean_settings:
        return JsonResponse({'success': False, 'error': 'Invalid setting'}, status=400)

    setattr(settings, name, setting_value)
    settings.save(update_fields=[name, 'updated_at'])

    response = HttpResponse(status=204)
    response['HX-Trigger'] = json.dumps({
        'showToast': {'message': str(_('Setting saved')), 'color': 'success'},
    })
    return response


@login_required
@require_POST
def settings_reset(request):
    hub = _hub_id(request)
    settings = LoyaltySettings.get_settings(hub)

    settings.program_name = 'Loyalty Program'
    settings.program_enabled = True
    settings.points_per_currency = Decimal('1.00')
    settings.points_value = Decimal('0.01')
    settings.minimum_redemption = 100
    settings.points_expire = False
    settings.expiry_months = 12
    settings.auto_enroll = True
    settings.welcome_points = 0
    settings.show_points_on_receipt = True
    settings.show_available_rewards = True
    settings.save()

    from django.shortcuts import render
    response = render(request, 'loyalty/partials/settings_form.html', {
        'settings': settings,
    })
    response['HX-Trigger'] = json.dumps({
        'showToast': {'message': str(_('Settings reset to defaults')), 'color': 'warning'},
    })
    return response


# =============================================================================
# API Endpoints (for POS integration)
# =============================================================================

@login_required
@require_GET
def api_member_search(request):
    hub = _hub_id(request)
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'members': []})

    members = LoyaltyMember.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).filter(
        Q(member_number__icontains=query) |
        Q(card_number__icontains=query) |
        Q(phone__icontains=query) |
        Q(name__icontains=query)
    ).select_related('tier')[:10]

    results = [{
        'id': str(m.pk),
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


@login_required
@require_GET
def api_member_balance(request, pk):
    hub = _hub_id(request)
    member = get_object_or_404(
        LoyaltyMember.objects.select_related('tier'),
        pk=pk, hub_id=hub, is_deleted=False, is_active=True,
    )
    settings = LoyaltySettings.get_settings(hub)

    return JsonResponse({
        'id': str(member.pk),
        'member_number': member.member_number,
        'name': member.name,
        'points_balance': member.points_balance,
        'points_value': float(settings.calculate_points_value(member.points_balance)),
        'tier': {
            'name': member.tier.name,
            'color': member.tier.color,
            'discount_percent': float(member.tier.discount_percent),
            'points_multiplier': float(member.tier.points_multiplier),
        } if member.tier else None,
    })


@login_required
@require_GET
def api_available_rewards(request, member_id):
    hub = _hub_id(request)
    member = get_object_or_404(
        LoyaltyMember, pk=member_id, hub_id=hub, is_deleted=False, is_active=True,
    )

    rewards = Reward.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('points_cost')

    results = []
    for reward in rewards:
        can_redeem, reason = reward.can_redeem(member)
        results.append({
            'id': str(reward.pk),
            'name': reward.name,
            'points_cost': reward.points_cost,
            'reward_type': reward.reward_type,
            'value': float(reward.value),
            'can_redeem': can_redeem,
            'reason': str(reason) if reason else None,
        })

    return JsonResponse({'rewards': results})
