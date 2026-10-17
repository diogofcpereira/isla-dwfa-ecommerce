import pytest
from django.db import IntegrityError

from shop.factories import (CategoryFactory, OrderFactory,
                            OrderItemFactory, ProductFactory)
from shop.models import OrderItem
from shop.services import OutOfStock, add_item, categories_with_counts


@pytest.mark.django_db
def test_same_product_twice_in_an_order_is_rejected():
    item = OrderItemFactory()
    with pytest.raises(IntegrityError):
        OrderItemFactory(order=item.order, product=item.product)


@pytest.mark.django_db
def test_category_list_with_counts_has_no_n_plus_one(
        django_assert_max_num_queries):
    for category in CategoryFactory.create_batch(5):
        ProductFactory.create_batch(4, category=category)
    with django_assert_max_num_queries(2):
        rows = list(categories_with_counts())
    assert len(rows) == 5 and all(r.n == 4 for r in rows)


@pytest.mark.django_db
def test_adding_more_than_stock_leaves_no_row():
    product = ProductFactory(stock=2)
    order = OrderFactory()
    with pytest.raises(OutOfStock):
        add_item(order, product, quantity=5)
    assert not OrderItem.objects.filter(order=order).exists()
    product.refresh_from_db()
    assert product.stock == 2