import pytest
from rest_framework.test import APIClient

from shop.factories import OrderFactory, OrderItemFactory, ProductFactory
from shop.models import OrderItem


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_product_list_is_paginated(api):
    ProductFactory.create_batch(25)
    response = api.get("/api/v1/products/")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"count", "next", "previous", "results"}
    assert body["count"] == 25 and len(body["results"]) == 20


@pytest.mark.django_db
def test_create_item_and_reject_quantity_above_stock(api):
    order = OrderFactory()
    product = ProductFactory(stock=3)
    ok = api.post("/api/v1/order-items/",
                  {"order": order.pk, "product": product.pk, "quantity": 2},
                  format="json")
    assert ok.status_code == 201
    assert OrderItem.objects.filter(order=order, product=product).exists()

    scarce = ProductFactory(stock=1)
    bad = api.post("/api/v1/order-items/",
                   {"order": order.pk, "product": scarce.pk, "quantity": 5},
                   format="json")
    assert bad.status_code == 400
    assert "quantity" in bad.json()


@pytest.mark.django_db
def test_order_list_is_paginated_without_n_plus_one(api, django_assert_max_num_queries):
    for order in OrderFactory.create_batch(25):
        OrderItemFactory.create_batch(3, order=order)
    with django_assert_max_num_queries(3):   # count + encomendas + linhas
        response = api.get("/api/v1/orders/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 25 and len(body["results"]) == 20