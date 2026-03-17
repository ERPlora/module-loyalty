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


@register_tool
class UpdateLoyaltyReward(AssistantTool):
    name = "update_loyalty_reward"
    description = "Update an existing loyalty reward."
    module_id = "loyalty"
    required_permission = "loyalty.change_loyaltymember"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "reward_id": {"type": "string", "description": "Reward ID"},
            "name": {"type": "string", "description": "Reward name"},
            "points_cost": {"type": "integer", "description": "Points required to redeem"},
            "reward_type": {"type": "string", "description": "discount_percent, discount_amount, free_product, free_shipping, gift_card"},
            "value": {"type": "string", "description": "Discount % or amount"},
            "is_active": {"type": "boolean", "description": "Whether the reward is active"},
            "is_featured": {"type": "boolean", "description": "Whether to feature the reward"},
            "max_redemptions": {"type": "integer", "description": "Max total redemptions (null = unlimited)"},
            "max_per_member": {"type": "integer", "description": "Max redemptions per member"},
        },
        "required": ["reward_id"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from decimal import Decimal
        from loyalty.models import Reward
        try:
            r = Reward.objects.get(id=args['reward_id'])
        except Reward.DoesNotExist:
            return {"error": "Reward not found"}
        fields = []
        if 'name' in args:
            r.name = args['name']
            fields.append('name')
        if 'points_cost' in args:
            r.points_cost = args['points_cost']
            fields.append('points_cost')
        if 'reward_type' in args:
            r.reward_type = args['reward_type']
            fields.append('reward_type')
        if 'value' in args:
            r.value = Decimal(args['value'])
            fields.append('value')
        if 'is_active' in args:
            r.is_active = args['is_active']
            fields.append('is_active')
        if 'is_featured' in args:
            r.is_featured = args['is_featured']
            fields.append('is_featured')
        if 'max_redemptions' in args:
            r.max_redemptions = args['max_redemptions']
            fields.append('max_redemptions')
        if 'max_per_member' in args:
            r.max_per_member = args['max_per_member']
            fields.append('max_per_member')
        if fields:
            fields.append('updated_at')
            r.save(update_fields=fields)
        return {"id": str(r.id), "name": r.name, "updated": True}


@register_tool
class DeleteLoyaltyReward(AssistantTool):
    name = "delete_loyalty_reward"
    description = "Delete (soft-delete) a loyalty reward."
    module_id = "loyalty"
    required_permission = "loyalty.change_loyaltymember"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "reward_id": {"type": "string", "description": "Reward ID"},
        },
        "required": ["reward_id"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from loyalty.models import Reward
        try:
            r = Reward.objects.get(id=args['reward_id'])
        except Reward.DoesNotExist:
            return {"error": "Reward not found"}
        name = r.name
        r.is_deleted = True
        r.is_active = False
        r.save(update_fields=['is_deleted', 'is_active', 'updated_at'])
        return {"deleted": True, "name": name}
