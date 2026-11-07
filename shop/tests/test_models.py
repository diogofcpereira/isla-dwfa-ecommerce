import pytest
from django.db import IntegrityError

from shop.factories import BrandFactory, CarFactory, OrderFactory, OrderItemFactory
from shop.models import OrderItem
from shop.services import OutOfStock, add_item, brands_with_counts


@pytest.mark.django_db
def test_same_car_twice_in_an_order_is_rejected():
    item = OrderItemFactory()
    with pytest.raises(IntegrityError):
        OrderItemFactory(order=item.order, car=item.car)


@pytest.mark.django_db
def test_brand_list_with_counts_has_no_n_plus_one(django_assert_max_num_queries):
    for brand in BrandFactory.create_batch(5):
        CarFactory.create_batch(4, brand=brand)
    with django_assert_max_num_queries(2):
        rows = list(brands_with_counts())
    assert len(rows) == 5 and all(r.n == 4 for r in rows)


@pytest.mark.django_db
def test_adding_more_than_stock_leaves_no_row():
    car = CarFactory(stock=2)
    order = OrderFactory()
    with pytest.raises(OutOfStock):
        add_item(order, car, quantity=5)
    assert not OrderItem.objects.filter(order=order).exists()
    car.refresh_from_db()
    assert car.stock == 2


@pytest.mark.django_db
def test_add_item_copies_price_and_decrements_stock():
    car = CarFactory(stock=4)
    item = add_item(OrderFactory(), car, quantity=3)
    car.refresh_from_db()
    assert car.stock == 1
    assert item.unit_price == car.price


@pytest.mark.django_db
def test_car_name_joins_brand_model_and_version():
    car = CarFactory(brand=BrandFactory(name="Toyota", slug="toyota"), model="Yaris", version="")
    assert car.name == "Toyota Yaris"
