"""
Extracts/scrapes the desired information from the required product.
"""
import json
from os import environ

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests


def scrape_asos_page(url: str, header: dict) -> dict:
    """
    Scrapes an ASOS page and returns a dict of desired data about the product.
    """
    page = requests.get(url, headers=header)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")
    product_data = json.loads(soup.string)
    print(product_data)

    price_endpoint = f"https://www.asos.com/api/product/catalogue/v3/stockprice?productIds={product_data['productID']}&store=COM&currency=GBP"

    price = requests.get(price_endpoint).json()[
        0]["productPrice"]["current"]["text"]

    wanted_prod_data = {
        "product_name": product_data["name"],
        "image_URL": product_data["image"],
        "price": price
    }

    return wanted_prod_data


if __name__ == "__main__":

    load_dotenv()

    header = {
        'authority':  environ["AUTHORITY"],
        'user-agent': environ["USER_AGENT"]
    }

    print(scrape_asos_page(environ["EXAMPLE_PAGE"], header))
