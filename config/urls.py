from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from core.views import health
from shop import views

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
]
