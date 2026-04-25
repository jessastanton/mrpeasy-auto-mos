import requests
import json
import logging
from requests.auth import HTTPBasicAuth
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

API_KEY = os.environ.get("MRPEASY_API_KEY", "g56756j8beefcd961")
API_SECRET = os.environ.get("MRPEASY_API_SECRET", "3%:?pU7LU.{Tl{qi~^XWI~!4e5Kb")
BASE_URL = "https://api.mrpeasy.com/rest/v1"
SITE_ID = 1
ASSIGNED_ID = 4  # jessica

# Kit article IDs — add any new 2-pack or bundle SKUs here
KIT_ARTICLE_IDS = {8068}  # 810003239525 Veal Chop 14-16oz - 2 Pack

auth = HTTPBasicAuth(API_KEY, API_SECRET)
headers = {"Content-Type": "application/json"}


def get_confirmed_unbooked_orders():
    r = requests.get(f"{BASE_URL}/customer-orders", auth=auth, headers=headers)
    if r.status_code not in (200, 206):
        log.error(f"Failed to fetch customer orders: {r.status_code} {r.text[:200]}")
        return []
    orders = r.json()
    # status "30" = Confirmed, part_status "10" = Not booked
    confirmed = [o for o in orders if o.get("status") == "30" and o.get("part_status") == "10"]
    log.info(f"Total orders returned: {len(orders)}, Confirmed+unbooked: {len(confirmed)}")
    return confirmed


def get_existing_mo_line_ids(cust_ord_id):
    r = requests.get(f"{BASE_URL}/manufacturing-orders?cust_ord_id={cust_ord_id}", auth=auth, headers=headers)
    if r.status_code not in (200, 206):
        return set()
    mos = r.json()
    return {mo.get("cust_ord_line_id") for mo in mos if mo.get("cust_ord_line_id")}


def create_mo(article_id, quantity, cust_ord_id, line_id):
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
    log.info("Checking for unbooked confirmed orders with kit items...")
    orders = get_confirmed_unbooked_orders()

    if not orders:
        log.info("No confirmed unbooked orders found.")
        return

    for order in orders:
        cust_ord_id = order["cust_ord_id"]
        code = order["code"]
        existing_line_ids = get_existing_mo_line_ids(cust_ord_id)

        for line in order.get("products", []):
            line_id = line["line_id"]
            article_id = line["article_id"]
            quantity = line["quantity"]
            item_title = line["item_title"]

            if line_id in existing_line_ids:
                log.info(f"MO already exists for {code} line {line_id} ({item_title}), skipping")
                continue

            if article_id not in KIT_ARTICLE_IDS:
                continue

            log.info(f"Creating MO for {code} - {item_title} (qty: {quantity})")
            status, response = create_mo(article_id, quantity, cust_ord_id, line_id)

            if status == 201:
                log.info(f"✅ MO {response.strip()} created for {code} - {item_title}")
            else:
                log.error(f"❌ Failed to create MO for {code} - {item_title}: {status} {response}")

    log.info("Done.")


if __name__ == "__main__":
    run()
