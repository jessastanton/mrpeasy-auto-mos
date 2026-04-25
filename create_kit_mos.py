import requests
import json
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

PROCESSED_FILE = "processed_lines.json"

auth = HTTPBasicAuth(API_KEY, API_SECRET)
headers = {"Content-Type": "application/json"}


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(sorted(list(processed)), f)


def get_confirmed_unbooked_orders():
    r = requests.get(f"{BASE_URL}/customer-orders", auth=auth, headers=headers)
    if r.status_code not in (200, 206):
        log.error(f"Failed to fetch orders: {r.status_code}")
        return []
    orders = r.json()
    confirmed = [o for o in orders if o.get("status") == "30" and o.get("part_status") == "10"]
    log.info(f"Total orders: {len(orders)}, Confirmed+unbooked: {len(confirmed)}")
    return confirmed


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
    processed = load_processed()
    log.info(f"Already processed line IDs: {processed}")
    orders = get_confirmed_unbooked_orders()
    changed = False

    for order in orders:
        cust_ord_id = order["cust_ord_id"]
        code = order["code"]

        for line in order.get("products", []):
            line_id = line["line_id"]
            article_id = line["article_id"]
            quantity = line["quantity"]
            item_title = line["item_title"]

            if article_id not in KIT_ARTICLE_IDS:
                continue

            key = str(line_id)
            if key in processed:
                log.info(f"Already processed {code} line {line_id} ({item_title}), skipping")
                continue

            log.info(f"Creating MO for {code} - {item_title} (qty: {quantity})")
            status, response = create_mo(article_id, quantity, cust_ord_id, line_id)

            if status == 201:
                log.info(f"✅ MO {response.strip()} created for {code} - {item_title}")
                processed.add(key)
                changed = True
            else:
                log.error(f"❌ Failed: {status} {response}")

    if changed:
        save_processed(processed)
        log.info(f"Saved processed lines: {processed}")

    log.info("Done.")


if __name__ == "__main__":
    run()
