"""
Extracts/scrapes the desired information from the required product.
"""
import json
from os import environ
from urllib.parse import urlparse


from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests


def get_domain_name(url: str) -> str:
    """
    Returns the domain name of the url.
    """
    parsed_url = urlparse(url)
    domain_name = '{uri.netloc}'.format(uri=parsed_url)
    return domain_name


def scrape_asos_page(url: str, header: dict) -> dict:
    """
    Scrapes an ASOS page and returns a dict of desired data about the product.
    """
    page = requests.get(url, headers=header)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")
    product_data = json.loads(soup.string)

    domain_name = get_domain_name(url)

    wanted_prod_data = {
        "product_name": product_data["name"],
        "image_URL": product_data["image"],
        "product_url": url,
        "website_name": domain_name
    }

    price_endpoint = f"https://www.asos.com/api/product/catalogue/v3/stockprice?productIds={product_data['productID']}&store=COM&currency=GBP"

    price = requests.get(price_endpoint).json()[
        0]["productPrice"]["current"]["value"]

    if price:
        wanted_prod_data["price"] = price
    else:
        wanted_prod_data["price"] = "Price not found"

    return wanted_prod_data


if __name__ == "__main__":

    load_dotenv()

    header = {
        'authority':  environ["AUTHORITY"],
        'user-agent': environ["USER_AGENT"]
    }

    print(scrape_asos_page(environ["EXAMPLE_PAGE"], header))
