# shop/permissions.py
"""Regras de acesso da loja: quem pode fazer o quê.

Papéis:
- anónimo: só lê o catálogo (categorias e produtos);
- cliente: qualquer utilizador autenticado; só mexe nas suas encomendas;
- gestor: pertence ao grupo 'gestores' (criado na migração 0002); pode tudo.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

GESTORES = "gestores"


def is_gestor(user):
    """True se o utilizador estiver autenticado e pertencer ao grupo 'gestores'."""
    return user.is_authenticated and user.groups.filter(name=GESTORES).exists()


class IsGestor(BasePermission):
    """Só gestores."""

    def has_permission(self, request, view):
        return is_gestor(request.user)


class IsGestorOrReadOnly(BasePermission):
    """Leitura para todos (catálogo público); escrita só para gestores."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:   # GET, HEAD, OPTIONS
            return True
        return is_gestor(request.user)


class IsOwnerOrGestor(BasePermission):
    """Por objeto, para Order: o gestor pode tudo; o cliente só mexe nas suas."""

    def has_object_permission(self, request, view, obj):
        return is_gestor(request.user) or obj.customer.user_id == request.user.id


class IsItemOwnerOrGestor(BasePermission):
    """Por objeto, para OrderItem: o dono é o dono da encomenda a que a linha pertence."""

    def has_object_permission(self, request, view, obj):
        return is_gestor(request.user) or obj.order.customer.user_id == request.user.id