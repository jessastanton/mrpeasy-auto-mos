import requests
import logging
import os
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

API_KEY = os.environ.get("MRPEASY_API_KEY", "g56756j8beefcd961")
API_SECRET = os.environ.get("MRPEASY_API_SECRET", "3%:?pU7LU.{Tl{qi~^XWI~!4e5Kb")
BASE_URL = "https://api.mrpeasy.com/rest/v1"
SITE_ID = 1
ASSIGNED_ID = 4  # jessica

# Kit article IDs — add new bundle SKUs here as needed
KIT_ARTICLE_IDS = {8068}  # 810003239525 Veal Chop 14-16oz - 2 Pack

auth = HTTPBasicAuth(API_KEY, API_SECRET)
headers = {"Content-Type": "application/json"}


def get_confirmed_unbooked_orders():
    r = requests.get(f"{BASE_URL}/customer-orders", auth=auth, headers=headers)
    if r.status_code not in (200, 206):
        log.error(f"Failed to fetch orders: {r.status_code}")
        return []
    orders = r.json()
    confirmed = [o for o in orders if o.get("status") == "30" and o.get("part_status") == "10"]
    log.info(f"Total orders: {len(orders)}, Confirmed+unbooked: {len(confirmed)}")
    return confirmed


def get_existing_mo_article_ids(cust_ord_id):
    """Return set of article_ids that already have an MO for this customer order."""
    r = requests.get(f"{BASE_URL}/manufacturing-orders?cust_ord_id={cust_ord_id}", auth=auth, headers=headers)
    if r.status_code not in (200, 206):
        return set()
    try:
        mos = r.json()
        return {mo.get("article_id") for mo in mos if mo.get("article_id")}
    except Exception:
        return set()


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
    log.info("Checking for unbooked confirmed kit orders...")
    orders = get_confirmed_unbooked_orders()

    for order in orders:
        cust_ord_id = order["cust_ord_id"]
        code = order["code"]

        # Get article_ids that already have MOs for this order
        existing_article_ids = get_existing_mo_article_ids(cust_ord_id)

        for line in order.get("products", []):
            line_id = line["line_id"]
            article_id = line["article_id"]
            quantity = line["quantity"]
            item_title = line["item_title"]

            if article_id not in KIT_ARTICLE_IDS:
                continue

            if article_id in existing_article_ids:
                log.info(f"MO already exists for {code} - {item_title}, skipping")
                continue

            log.info(f"Creating MO for {code} - {item_title} (qty: {quantity})")
            status, response = create_mo(article_id, quantity, cust_ord_id, line_id)

            if status == 201:
                log.info(f"✅ MO {response.strip()} created for {code} - {item_title}")
            else:
                log.error(f"❌ Failed: {status} {response}")

    log.info("Done.")


if __name__ == "__main__":
    run()
