import base64
import json
import time
import requests

# ---------------------------------------------------------
# JOHNNY'S CUSTOMIZED CREDENTIALS
# ---------------------------------------------------------
EBAY_CLIENT_ID = "JohnnyGo-Tcg-PRD-e448c4893-6fae34da"
EBAY_CLIENT_SECRET = "PRD-448c48931719-d55d-4d10-b9ae-34d3"
DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1543963910045175808/"
    "IECC93pYegkhktN95SQojnJjxVtxVZxQsbWgKKKvu9JmxW6oqVeq6c7fbbym5X0us8U4"
)

# Search Settings
SEARCH_KEYWORDS = "Pokemon card"
CATEGORY_ID = "183454"  # CCG Individual Cards category
POLL_INTERVAL_SECONDS = 180  # Check for new items every 3 minutes

seen_item_ids = set()


def get_ebay_oauth_token():
    auth_header = base64.b64encode(
        f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()
    ).decode()
    url = "https://api.ebay.com/identity/v1/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_header}",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"[-] Authentication Failed: {response.text}")
        return None


def send_discord_alert(title, price, shipping, item_url, image_url, reason):
    total_price = price + shipping
    payload = {
        "embeds": [
            {
                "title": f"🚨 DEAL ALERT: {title}",
                "url": item_url,
                "color": 3066993,  
                "thumbnail": {"url": image_url},
                "fields": [
                    {"name": "Listing Price", "value": f"${price:.2f}", "inline": True},
                    {"name": "Shipping", "value": f"${shipping:.2f}", "inline": True},
                    {"name": "Total Cost", "value": f"**${total_price:.2f}**", "inline": True},
                    {"name": "Trigger Reason", "value": reason, "inline": False},
                ],
                "footer": {"text": "Johnny's eBay Card Monitor"},
            }
        ]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print(f"[+] Alert sent to Discord for: {title}")
    except Exception as e:
        print(f"[-] Failed to send Discord alert: {e}")


def load_target_prices():
    try:
        with open("target_cards.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[-] Error loading target_cards.json: {e}")
        return {}


def check_ebay_deals(access_token):
    target_prices = load_target_prices()
    if not target_prices:
        return

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }
    params = {
        "q": SEARCH_KEYWORDS,
        "category_ids": CATEGORY_ID,
        "filter": "buyingOptions:{FIXED_PRICE}",
        "sort": "newlyListed",
        "limit": 20,
    }

    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        return

    data = res.json()
    items = data.get("itemSummaries", [])

    for item in items:
        item_id = item.get("itemId")
        if item_id in seen_item_ids:
            continue

        title = item.get("title", "")
        item_url = item.get("itemWebUrl", "")
        price = float(item.get("price", {}).get("value", 0.0))

        shipping_options = item.get("shippingOptions", [])
        shipping_cost = float(shipping_options[0].get("shippingCost", {}).get("value", 0.0)) if shipping_options else 0.0
        total_cost = price + shipping_cost
        image_url = item.get("image", {}).get("imageUrl", "")

        for keyword, max_target_price in target_prices.items():
            # Check if all words in the keyword are present in the title
            if all(word.lower() in title.lower() for word in keyword.split()):
                if total_cost <= max_target_price:
                    reason = f"Matched '{keyword}' under target price of ${max_target_price:.2f}"
                    send_discord_alert(title, price, shipping_cost, item_url, image_url, reason)
                break

        seen_item_ids.add(item_id)


def main():
    print("Starting Johnny's Pokémon Card Monitor...")
    token = get_ebay_oauth_token()
    if not token:
        return

    print("[+] Successfully authenticated with eBay API!")
    token_time = time.time()

    while True:
        try:
            if time.time() - token_time > 5400:
                print("[*] Refreshing OAuth Token...")
                token = get_ebay_oauth_token()
                token_time = time.time()
            check_ebay_deals(token)
        except Exception as e:
            print(f"[-] Unexpected loop error: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
