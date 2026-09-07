import json
import os

from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401
from app.models import Vendor, PurchaseOrder, POLineItem
from app.utils.normalize import normalize_vendor_name

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data")


def load_json(filename):
    path = os.path.join(SAMPLE_DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Vendor).count() > 0:
            print("Seed data already present, skipping.")
            return

        vendors_data = load_json("vendors.json")
        vendor_id_map = {}

        for v in vendors_data:
            vendor = Vendor(
                name=v["name"],
                normalized_name=normalize_vendor_name(v["name"]),
                tax_id=v["tax_id"],
            )
            db.add(vendor)
            db.flush()
            vendor_id_map[v["id"]] = vendor.id

        purchase_orders_data = load_json("purchase_orders.json")

        for po in purchase_orders_data:
            purchase_order = PurchaseOrder(
                po_number=po["po_number"],
                vendor_id=vendor_id_map[po["vendor_id"]],
                currency=po["currency"],
                total_amount=po["total_amount"],
                invoiced_amount=po["invoiced_amount"],
                status=po["status"],
            )
            db.add(purchase_order)
            db.flush()

            for line in po["line_items"]:
                db.add(
                    POLineItem(
                        po_id=purchase_order.id,
                        description=line["description"],
                        quantity=line["quantity"],
                        unit_price=line["unit_price"],
                        amount=line["amount"],
                    )
                )

        db.commit()
        print(f"Seeded {len(vendors_data)} vendors and {len(purchase_orders_data)} purchase orders.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
