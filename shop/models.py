# Create your models here.
from django.conf import settings
from django.db import models
from django.db.models import Q


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products")
    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0), name="ck_product_price_gte_0"),
        ]
        indexes = [
            models.Index(fields=["category", "is_active"],
                         name="ix_product_category_active"),
        ]

    def __str__(self):
        return self.name


class Customer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="customer")
    phone = models.CharField(max_length=20, blank=True)
    shipping_address = models.TextField(blank=True)

    def __str__(self):
        return self.user.get_username()


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Paga"
        SHIPPED = "shipped", "Enviada"
        CANCELLED = "cancelled", "Cancelada"

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(
        max_length=10, choices=Status, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"],
                         name="ix_order_customer_status"),
        ]

    def __str__(self):
        return f"Encomenda #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="uq_orderitem_order_product"),
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="ck_orderitem_quantity_gte_1"),
        ]


class Payment(models.Model):
    class Method(models.TextChoices):
        CARD = "card", "Cartão"
        MBWAY = "mbway", "MB WAY"
        TRANSFER = "transfer", "Transferência"

    order = models.OneToOneField(
        Order, on_delete=models.PROTECT, related_name="payment")
    method = models.CharField(max_length=10, choices=Method)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="ck_payment_amount_gt_0"),
        ]