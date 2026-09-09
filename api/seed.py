"""
Populates the DB with a handful of sample products and 60 days of
synthetic (but realistic-looking) price history, so /products,
/products/{id}/history and /products/{id}/predict all return real data.

Run once after your tables exist:
    python seed.py
"""
import random
from datetime import datetime, timedelta

from database import Base, SessionLocal, engine
from models import Product, PriceHistory

Base.metadata.create_all(bind=engine)

SAMPLE_PRODUCTS = [
    dict(name="Sony WH-1000XM5 Headphones", category="Electronics", currency="INR", current_price=26990),
    dict(name="Instant Pot Duo 6-Qt", category="Home & Kitchen", currency="INR", current_price=7999),
    dict(name="Nike Air Zoom Pegasus 40", category="Footwear", currency="INR", current_price=8995),
    dict(name="Logitech MX Master 3S", category="Electronics", currency="INR", current_price=8995),
    dict(name="Dyson V11 Vacuum Cleaner", category="Home & Kitchen", currency="INR", current_price=32900),
    dict(name="Kindle Paperwhite (11th Gen)", category="Electronics", currency="INR", current_price=13999),
]


def gen_history(base_price: float, days: int = 60, trend: str = "down"):
    """Generate a plausible daily price series with noise and an overall trend."""
    points = []
    price = base_price * (1.08 if trend == "down" else 0.92)
    drift = (base_price - price) / days
    for i in range(days):
        noise = random.uniform(-0.01, 0.01) * price
        price = max(price + drift + noise, base_price * 0.7)
        recorded_at = datetime.utcnow() - timedelta(days=days - i)
        points.append((recorded_at, round(price, 2)))
    points.append((datetime.utcnow(), base_price))
    return points


def main():
    db = SessionLocal()
    try:
        if db.query(Product).count() > 0:
            print("Products already exist — skipping seed. Delete rows first if you want to reseed.")
            return

        for i, data in enumerate(SAMPLE_PRODUCTS):
            product = Product(**data)
            db.add(product)
            db.flush()  # get product.id before commit

            trend = "down" if i % 2 == 0 else "up"
            for recorded_at, price in gen_history(data["current_price"], trend=trend):
                db.add(PriceHistory(product_id=product.id, price=price, recorded_at=recorded_at))

        db.commit()
        print(f"Seeded {len(SAMPLE_PRODUCTS)} products with 60 days of price history each.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
