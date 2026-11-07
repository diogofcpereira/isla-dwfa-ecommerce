"""Domínio DriveNow — stand de carros.

Seis entidades: Brand (marca), Car (viatura), Customer (cliente), Order (encomenda),
OrderItem (linha da encomenda) e Payment (pagamento). Todas as FKs têm um `on_delete`
deliberado e um `related_name`; as regras que a base de dados consegue garantir ficam
em constraints, não só no código.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q


class Brand(models.Model):
    """Marca de automóveis (Volkswagen, Renault, …). O catálogo agrupa-se por marca."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Car(models.Model):
    """Viatura à venda: uma versão de um modelo, com as unidades disponíveis em stock."""

    class Fuel(models.TextChoices):
        PETROL = "petrol", "Gasolina"
        DIESEL = "diesel", "Gasóleo"
        HYBRID = "hybrid", "Híbrido"
        ELECTRIC = "electric", "Elétrico"

    # PROTECT: não se apaga uma marca que ainda tem viaturas no catálogo.
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="cars")
    code = models.CharField(max_length=32, unique=True)  # código interno do stand
    model = models.CharField(max_length=80)  # ex.: "Golf"
    version = models.CharField(max_length=80, blank=True)  # ex.: "1.5 eTSI Life"
    year = models.PositiveSmallIntegerField()
    fuel = models.CharField(max_length=10, choices=Fuel)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)  # unidades disponíveis
    is_active = models.BooleanField(default=True)  # False = retirada do catálogo
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["brand__name", "model", "version"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="ck_car_price_gte_0"),
            models.CheckConstraint(condition=Q(year__gte=1990), name="ck_car_year_gte_1990"),
        ]
        indexes = [
            models.Index(fields=["brand", "is_active"], name="ix_car_brand_active"),
            models.Index(fields=["fuel", "price"], name="ix_car_fuel_price"),
        ]

    def __str__(self):
        return self.name

    @property
    def name(self):
        """Nome legível: "Volkswagen Golf 1.5 eTSI Life"."""
        return " ".join(p for p in [self.brand.name, self.model, self.version] if p)


class Customer(models.Model):
    """Perfil de cliente de um utilizador: o dono das suas encomendas."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer"
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.user.get_username()


class Order(models.Model):
    """Encomenda de uma ou mais viaturas, feita por um cliente."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Paga"
        DELIVERED = "delivered", "Entregue"
        CANCELLED = "cancelled", "Cancelada"

    # PROTECT: uma encomenda é um registo comercial; não desaparece com o cliente.
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"], name="ix_order_customer_status"),
        ]

    def __str__(self):
        return f"Encomenda #{self.pk}"


class OrderItem(models.Model):
    """Linha de uma encomenda: uma viatura, a quantidade e o preço no momento da compra."""

    # CASCADE: uma linha não existe sem a encomenda.
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # PROTECT: uma viatura já vendida não se apaga; retira-se com is_active=False.
    car = models.ForeignKey(Car, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "car"], name="uq_orderitem_order_car"),
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name="ck_orderitem_quantity_gte_1"
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.car.name}"


class Payment(models.Model):
    """Pagamento de uma encomenda (um por encomenda)."""

    class Method(models.TextChoices):
        TRANSFER = "transfer", "Transferência"
        FINANCING = "financing", "Financiamento"
        CARD = "card", "Cartão"
        MBWAY = "mbway", "MB WAY"

    # PROTECT: não se apaga uma encomenda que já tem um pagamento registado.
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    method = models.CharField(max_length=10, choices=Method)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="ck_payment_amount_gt_0"),
        ]

    def __str__(self):
        return f"Pagamento da encomenda #{self.order_id}"
