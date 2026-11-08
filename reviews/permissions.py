from rest_framework.permissions import SAFE_METHODS, BasePermission

from shop.permissions import is_gestor


class IsReviewAuthorOrGestor(BasePermission):
    """Por objeto: todos leem o que veem; só o autor (ou o gestor) altera ou apaga."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return is_gestor(request.user) or obj.customer.user_id == request.user.id
