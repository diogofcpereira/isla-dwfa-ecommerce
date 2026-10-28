from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_gestor(user):
    """True se o utilizador estiver autenticado e pertencer ao grupo 'gestores'."""
    return user.is_authenticated and user.groups.filter(name="gestores").exists()


class IsGestor(BasePermission):
    def has_permission(self, request, view):
        return is_gestor(request.user)


class IsGestorOrReadOnly(BasePermission):
    """Leitura para todos; escrita só para gestores."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:   # GET, HEAD, OPTIONS
            return True
        return is_gestor(request.user)


class IsOwnerOrGestor(BasePermission):
    """Por objeto: o gestor pode tudo; o cliente só mexe no que é dele."""
    def has_object_permission(self, request, view, obj):
        return is_gestor(request.user) or obj.customer.user_id == request.user.id