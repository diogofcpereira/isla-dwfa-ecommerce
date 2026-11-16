from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import MeView, ThrottledTokenView
from core.views import health
from shop import views
from shop.reports import OrdersReportView, TaskStatusView

router = DefaultRouter()
router.register("categories", views.CategoryViewSet)
router.register("products", views.ProductViewSet)
router.register("orders", views.OrderViewSet, basename="order")
router.register("order-items", views.OrderItemViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/v1/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # Autenticação (Ficha 03)
    path("api/v1/auth/token/", ThrottledTokenView.as_view(), name="token"),  # login com throttle
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api/v1/me/", MeView.as_view(), name="me"),
    # Ficha 05 · Parte 2: relatório em segundo plano (202) e o estado da tarefa
    path("api/v1/reports/orders/", OrdersReportView.as_view(), name="orders-report"),
    path("api/v1/tasks/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
]
