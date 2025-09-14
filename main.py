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

    # Get all products
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/products.json?limit=50"
    products = requests.get(url, headers=headers).json()["products"]

    import json
    from tqdm import tqdm
    for product in tqdm(products, desc="Processing products", unit="product"):
        product_meta = get_product_metafields(product["id"])

        # Convert values safely
        gold_weight = float(product_meta.get("gold_weight", 0))
        diamond_weight = float(product_meta.get("diamond_weight", 0))
        solitaire_count = float(product_meta.get("diamond_solitaire_count", 0))

        # Detect metal from variant option (14KT / 18KT)
        for idx, variant in enumerate(product["variants"]):
            field = "option3"  # Metal option should always be in option3 either it would fail
            metal_value = variant[field]
            if metal_value == "14 KT":
                gold_rate = float(shop_meta.get("fourteen_kt_gold_value_in_inr", 0))
                making_charges_percentage = float(shop_meta.get("fourteen_kt_making_charges_rate_percentage_in_inr", 0))
                
            elif metal_value == "18 KT":
                gold_rate = float(shop_meta.get("eighteen_kt_gold_value_in_inr", 0))
                making_charges_percentage = float(shop_meta.get("eighteen_kt_making_charges_rate_percentage_in_inr", 0))

            else:
                gold_rate = 0

            # Calculate price
            gold_value = gold_weight * gold_rate
            diamond_value = (diamond_weight * float(shop_meta.get("diamond_value_in_rs", 0))) + (solitaire_count * float(shop_meta.get("solitaire_value_in_rs", 0)))

            making_charges = gold_value * making_charges_percentage

            price = gold_value + diamond_value + making_charges
            tax = price * float(shop_meta.get("tax_percentage_in_inr", 0)) / 100
            final_price = price + tax #FINAL Price

            prev_price = float(variant.get("price", 0)) #PREVIOUS Price

            # Only update if price has changed
            if prev_price != final_price:
                # Update variant price
                resp = update_variant_price(variant["id"], final_price)
                # Get product and variant names for logging
                variant_name = variant.get("title") or variant.get("name") or variant.get("option1") or "Unknown"
                product_name = product.get("title") or product.get("name") or "Unknown Product"
                log_entry = f"✅ Product: {product_name} | Variant ID: {variant['id']}, Name: {variant_name}, Previous Price: {prev_price}, New Price: {final_price}\n"
                
                # Add log entry to file
                if "variant" in resp:
                    with open("price_update_log.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(log_entry)
                else:
                    with open("price_update_log.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(f"❌ Failed for {variant['id']} → {resp}\n")


if __name__ == "__main__":
    recalc_prices()

