import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
API_VERSION = "2025-01"   # use latest

# API setup
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

# Fetch shop-level metafields (gold rate, diamond rate, etc.)
def get_shop_metafields():
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/metafields.json"
    res = requests.get(url, headers=headers).json()
    return {m["key"]: m["value"] for m in res["metafields"]}

# Fetch product metafields
def get_product_metafields(product_id):
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/products/{product_id}/metafields.json"
    res = requests.get(url, headers=headers).json()
    return {m["key"]: m["value"] for m in res["metafields"]}

# Update variant price
def update_variant_price(variant_id, new_price):
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/variants/{variant_id}.json"
    payload = {
        "variant": {
            "id": variant_id,
            "price": str(round(new_price, 2))
        }
    }
    res = requests.put(url, json=payload, headers=headers)
    return res.json()

# Main processing
def recalc_prices():
    shop_meta = get_shop_metafields()
    # print("Shop metafields loaded:", shop_meta.keys())

    # Get all products
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/products.json?limit=50"
    products = requests.get(url, headers=headers).json()["products"]

    # print(f"Processing {len(products)} products...")
    # print(products)

    import json
    for product in products:
        print("Product ID:", product["id"], "Variants:", len(product["variants"]))
        product_meta = get_product_metafields(product["id"])
        # Convert values safely
        gold_weight = int(product_meta.get("gold_weight", 0))
        diamond_weight = int(product_meta.get("diamond_weight", 0))
        solitaire_count = int(product_meta.get("solitaire_count", 0))

        # Detect metal from variant option (14KT / 18KT)
        for idx, variant in enumerate(product["variants"]):
            field = "option3"
            metal_value = variant[field]
            if metal_value == "14 KT":
                # print("14 KT found")
                gold_rate = float(shop_meta.get("fourteen_kt_gold_value_in_inr", 0))
                
            elif metal_value == "18 KT":
                # print("18 KT found")
                gold_rate = float(shop_meta.get("eighteen_kt_gold_value_in_inr", 0))
                
            else:
                gold_rate = 0

            gold_value = gold_weight * gold_rate
            diamond_value = (diamond_weight * float(shop_meta.get("diamond_value_in_rs", 0))) + \
                            (solitaire_count * float(shop_meta.get("solitaire_value_in_rs", 0)))
            making_charges = gold_value * float(shop_meta.get("making_charge_rate_percentage_in_inr", 0))
            
            price = gold_value + diamond_value + making_charges
            tax = price * float(shop_meta.get("tax_percentage_in_inr", 0))
            final_price = price + tax

            resp = update_variant_price(variant["id"], final_price)
            # if "variant" in resp:
            #     print(f"✅ Updated variant {variant['id']} to {final_price}")
            # else:
            #     print(f"❌ Failed for {variant['id']} → {resp}")


if __name__ == "__main__":
    recalc_prices()
