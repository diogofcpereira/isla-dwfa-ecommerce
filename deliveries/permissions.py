from rest_framework.permissions import BasePermission

from shop.permissions import is_gestor


class IsDeliveryOwnerOrGestor(BasePermission):
    """Por objeto: o gestor pode tudo; o cliente só vê as entregas das suas encomendas."""

    def has_object_permission(self, request, view, obj):
        return is_gestor(request.user) or obj.order.customer.user_id == request.user.id
