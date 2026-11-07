import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from shop.factories import BrandFactory, CarFactory, CustomerFactory, OrderFactory, OrderItemFactory
from shop.models import Brand, Car, Customer, Order

# Catálogo de demonstração do DriveNow: (marca, modelo, versão, combustível, preço base).
CATALOGUE = [
    ("Volkswagen", "Golf", "1.5 eTSI Life", Car.Fuel.PETROL, "32500"),
    ("Volkswagen", "ID.3", "Pro 58 kWh", Car.Fuel.ELECTRIC, "39900"),
    ("Volkswagen", "Polo", "1.0 TSI Style", Car.Fuel.PETROL, "24900"),
    ("Renault", "Clio", "1.5 Blue dCi Evolution", Car.Fuel.DIESEL, "22800"),
    ("Renault", "Mégane E-Tech", "EV60 Techno", Car.Fuel.ELECTRIC, "41500"),
    ("Renault", "Captur", "E-Tech Full Hybrid", Car.Fuel.HYBRID, "30900"),
    ("Peugeot", "208", "1.2 PureTech Allure", Car.Fuel.PETROL, "23400"),
    ("Peugeot", "3008", "Hybrid 136 GT", Car.Fuel.HYBRID, "42700"),
    ("BMW", "Série 1", "118d M Sport", Car.Fuel.DIESEL, "38900"),
    ("BMW", "iX1", "eDrive20", Car.Fuel.ELECTRIC, "52300"),
    ("Mercedes-Benz", "Classe A", "A 180 d Progressive", Car.Fuel.DIESEL, "39600"),
    ("Mercedes-Benz", "GLA", "250 e AMG Line", Car.Fuel.HYBRID, "54900"),
    ("Toyota", "Yaris", "1.5 Hybrid Comfort", Car.Fuel.HYBRID, "23900"),
    ("Toyota", "Corolla", "1.8 Hybrid Exclusive", Car.Fuel.HYBRID, "33200"),
    ("Toyota", "C-HR", "2.0 Hybrid GR Sport", Car.Fuel.HYBRID, "41900"),
    ("Tesla", "Model 3", "RWD", Car.Fuel.ELECTRIC, "42990"),
    ("Tesla", "Model Y", "Long Range AWD", Car.Fuel.ELECTRIC, "52990"),
    ("SEAT", "Ibiza", "1.0 TSI FR", Car.Fuel.PETROL, "21900"),
    ("SEAT", "Leon", "2.0 TDI Xcellence", Car.Fuel.DIESEL, "33800"),
    ("Dacia", "Sandero", "1.0 TCe Expression", Car.Fuel.PETROL, "16200"),
]


class Command(BaseCommand):
    help = "Preenche a BD com dados de demonstração do DriveNow. Pode correr várias vezes."

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=40)
        parser.add_argument("--orders", type=int, default=150)

    @transaction.atomic
    def handle(self, *args, **opts):
        # Catálogo fixo: get_or_create pelo slug/código, por isso correr de novo não duplica.
        for i, (brand_name, model, version, fuel, price) in enumerate(CATALOGUE, start=1):
            brand = BrandFactory(name=brand_name, slug=slugify(brand_name))
            CarFactory(
                code=f"DN-{i:04d}",
                brand=brand,
                model=model,
                version=version,
                fuel=fuel,
                year=2024 + i % 3,  # 2024, 2025 ou 2026
                price=Decimal(price),
                stock=3 + i % 6,
            )
        cars = list(Car.objects.select_related("brand"))

        # Idempotente: só cria o que falta para chegar aos totais pedidos.
        missing = opts["customers"] - Customer.objects.count()
        CustomerFactory.create_batch(max(missing, 0))
        customers = list(Customer.objects.all())

        missing = opts["orders"] - Order.objects.count()
        for _ in range(max(missing, 0)):
            order = OrderFactory(customer=random.choice(customers))
            for car in random.sample(cars, k=random.randint(1, 3)):
                OrderItemFactory(order=order, car=car, quantity=random.randint(1, 2))

        self.stdout.write(
            self.style.SUCCESS(
                f"{Brand.objects.count()} marcas, "
                f"{Car.objects.count()} viaturas, "
                f"{Customer.objects.count()} clientes, "
                f"{Order.objects.count()} encomendas."
            )
        )
