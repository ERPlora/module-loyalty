"""AI tools for the Loyalty module."""
from assistant.tools import AssistantTool, register_tool


@register_tool
class ListLoyaltyMembers(AssistantTool):
    name = "list_loyalty_members"
    description = "List loyalty program members with optional search."
    module_id = "loyalty"
    required_permission = "loyalty.view_loyaltymember"
    parameters = {
        "type": "object",
        "properties": {
            "search": {"type": "string", "description": "Search by name, email, or member number"},
            "tier_id": {"type": "string", "description": "Filter by tier ID"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from loyalty.models import LoyaltyMember
        from django.db.models import Q
        qs = LoyaltyMember.objects.select_related('tier').filter(is_active=True)
        if args.get('search'):
            s = args['search']
            qs = qs.filter(Q(name__icontains=s) | Q(email__icontains=s) | Q(member_number__icontains=s))
        if args.get('tier_id'):
            qs = qs.filter(tier_id=args['tier_id'])
        limit = args.get('limit', 20)
        return {
            "members": [
                {
                    "id": str(m.id),
                    "member_number": m.member_number,
                    "name": m.name,
                    "email": m.email,
                    "tier": m.tier.name if m.tier else None,
                    "points_balance": m.points_balance,
                    "lifetime_points": m.lifetime_points,
                    "total_spent": str(m.total_spent) if m.total_spent else "0",
                    "visit_count": m.visit_count,
                }
                for m in qs.order_by('-lifetime_points')[:limit]
            ],
            "total": qs.count(),
        }


@register_tool
class GetLoyaltyMember(AssistantTool):
    name = "get_loyalty_member"
    description = "Get detailed info for a loyalty member by ID or member number."
    module_id = "loyalty"
    required_permission = "loyalty.view_loyaltymember"
    parameters = {
        "type": "object",
        "properties": {
            "member_id": {"type": "string", "description": "Member ID"},
            "member_number": {"type": "string", "description": "Member number"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from loyalty.models import LoyaltyMember
        if args.get('member_id'):
            m = LoyaltyMember.objects.get(id=args['member_id'])
        elif args.get('member_number'):
            m = LoyaltyMember.objects.get(member_number=args['member_number'])
        else:
            return {"error": "Provide member_id or member_number"}
        return {
            "id": str(m.id),
            "member_number": m.member_number,
            "name": m.name,
            "email": m.email,
            "phone": m.phone,
            "tier": m.tier.name if m.tier else None,
            "points_balance": m.points_balance,
            "lifetime_points": m.lifetime_points,
            "total_spent": str(m.total_spent) if m.total_spent else "0",
            "visit_count": m.visit_count,
            "enrolled_at": str(m.enrolled_at) if m.enrolled_at else None,
            "last_activity_at": str(m.last_activity_at) if m.last_activity_at else None,
        }


@register_tool
class AwardLoyaltyPoints(AssistantTool):
    name = "award_loyalty_points"
    description = "Award bonus points to a loyalty member."
    module_id = "loyalty"
    required_permission = "loyalty.change_loyaltymember"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "member_id": {"type": "string", "description": "Member ID"},
            "points": {"type": "integer", "description": "Points to award"},
            "description": {"type": "string", "description": "Reason for bonus points"},
        },
        "required": ["member_id", "points"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from loyalty.models import LoyaltyMember, PointsTransaction
        m = LoyaltyMember.objects.get(id=args['member_id'])
        m.points_balance += args['points']
        m.lifetime_points += args['points']
        m.save(update_fields=['points_balance', 'lifetime_points'])
        PointsTransaction.objects.create(
            member=m,
            transaction_type='bonus',
            points=args['points'],
            balance_after=m.points_balance,
            description=args.get('description', 'Bonus points from AI assistant'),
        )
        return {"member": m.name, "points_awarded": args['points'], "new_balance": m.points_balance}


@register_tool
class ListRewards(AssistantTool):
    name = "list_rewards"
    description = "List available loyalty rewards."
    module_id = "loyalty"
    required_permission = "loyalty.view_loyaltymember"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from loyalty.models import Reward
        rewards = Reward.objects.filter(is_active=True).order_by('points_cost')
        return {
            "rewards": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "points_cost": r.points_cost,
                    "reward_type": r.reward_type,
                    "value": str(r.value) if r.value else None,
                    "times_redeemed": r.times_redeemed,
                }
                for r in rewards
            ]
        }
