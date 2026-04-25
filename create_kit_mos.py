
import requests
import json
import logging
from requests.auth import HTTPBasicAuth
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

API_KEY = os.environ.get("MRPEASY_API_KEY", "g56756j8beefcd961")
API_SECRET = os.environ.get("MRPEASY_API_SECRET", "3%:?pU7LU.{Tl{qi~^XWI~!4e5Kb")
BASE_URL = "https://api.mrpeasy.com/rest/v1"
SITE_ID = 1
ASSIGNED_ID = 4  # jessica

auth = HTTPBasicAuth(API_KEY, API_SECRET)
headers = {"Content-Type": "application/json"}


def get_confirmed_unbooked_orders():
    """Fetch all confirmed customer orders that are not booked."""
    r = requests.get(f"{BASE_URL}/customer-orders", auth=auth, headers=headers)
    if r.status_code != 200:
        log.error(f"Failed to fetch customer orders: {r.status_code} {r.text}")
        return []
    orders = r.json()
    # status 30 = Confirmed, part_status 10 = Not booked
    return [o for o in orders if o.get("status") == "30" and o.get("part_status") == "10"]


def get_existing_mos_for_order(cust_ord_id):
    """Check if an MO already exists for this customer order to avoid duplicates."""
    r = requests.get(f"{BASE_URL}/manufacturing-orders?cust_ord_id={cust_ord_id}", auth=auth, headers=headers)
    if r.status_code != 200:
        return []
    return r.json()


def is_kit_item(article_id):
    """Check if the item has a BOM and no routing (i.e. it's a kit)."""
    r = requests.get(f"{BASE_URL}/items/{article_id}", auth=auth, headers=headers)
    if r.status_code != 200:
        return False
    item = r.json()
    # A kit has a BOM but no routing, and is not a procured item
    has_bom = bool(item.get("bom_id") or item.get("boms"))
    is_procured = item.get("is_procured", False)
    return has_bom and not is_procured


def create_mo(article_id, quantity, cust_ord_id, line_id):
    """Create a Manufacturing Order for a kit line item."""
    payload = {
        "article_id": article_id,
        "quantity": quantity,
        "cust_ord_id": cust_ord_id,
        "cust_ord_line_id": line_id,
        "site_id": SITE_ID,
        "assigned_id": ASSIGNED_ID
    }
    r = requests.post(f"{BASE_URL}/manufacturing-orders", auth=auth, json=payload)
    return r.status_code, r.text


def run():
    log.info("Checking for unbooked confirmed orders...")
    orders = get_confirmed_unbooked_orders()
    log.info(f"Found {len(orders)} confirmed unbooked orders")

    for order in orders:
        cust_ord_id = order["cust_ord_id"]
        code = order["code"]

        # Skip if MOs already exist for this order
        existing_mos = get_existing_mos_for_order(cust_ord_id)
        existing_line_ids = {mo.get("cust_ord_line_id") for mo in existing_mos}

        for line in order.get("products", []):
            line_id = line["line_id"]
            article_id = line["article_id"]
            quantity = line["quantity"]
            item_code = line["item_code"]
            item_title = line["item_title"]

            # Skip if MO already exists for this line
            if line_id in existing_line_ids:
                log.info(f"MO already exists for {code} line {line_id} ({item_title}), skipping")
                continue

            # Check if it's a kit
            if not is_kit_item(article_id):
                log.info(f"Item {item_code} ({item_title}) is not a kit, skipping")
                continue

            # Create the MO
            log.info(f"Creating MO for {code} - {item_title} (qty: {quantity})")
            status, response = create_mo(article_id, quantity, cust_ord_id, line_id)

            if status == 201:
                log.info(f"✅ MO {response.strip()} created for {code} - {item_title}")
            else:
                log.error(f"❌ Failed to create MO for {code} - {item_title}: {status} {response}")

    log.info("Done.")


if __name__ == "__main__":
    run()
