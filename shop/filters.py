import django_filters

from .models import Car


class CarFilter(django_filters.FilterSet):
    """Filtros do catálogo: marca, combustível, intervalo de preço e de ano."""

    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    min_year = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    max_year = django_filters.NumberFilter(field_name="year", lookup_expr="lte")

    class Meta:
        model = Car
        fields = ["brand", "fuel", "is_active"]
