from rest_framework.permissions import BasePermission

from shop.permissions import is_gestor


class IsTestDriveOwnerOrGestor(BasePermission):
    """Por objeto: o gestor pode tudo; o cliente só mexe nas suas marcações."""

    def has_object_permission(self, request, view, obj):
        return is_gestor(request.user) or obj.customer.user_id == request.user.id
