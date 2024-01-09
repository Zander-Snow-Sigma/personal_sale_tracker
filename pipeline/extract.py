"""
Extracts/scrapes the desired information from the required product.
"""
import json
from os import environ
from urllib.parse import urlparse


from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests

STARTER_ASOS_API = "https://www.asos.com/api/product/catalogue/v3/stockprice?"


def get_domain_name(url: str) -> str:
    """
    Returns the domain name of the url.
    """
    parsed_url = urlparse(url)
    domain_name = f'{parsed_url.netloc}'
    return domain_name


def scrape_asos_page(url: str, header: dict) -> dict:
    """
    Scrapes an ASOS page and returns a dict of desired data about the product.
    """
    domain_name = get_domain_name(url)
    page = requests.get(url, headers=header, timeout=5)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")
    try:
        product_data = json.loads(soup.string)

        wanted_prod_data = {
            "product_url": url,
            "website_name": domain_name
        }

        if "name" in product_data.keys():
            wanted_prod_data["product_name"] = product_data["name"]
        else:
            wanted_prod_data["product_name"] = product_data['@graph'][0]["name"]

        if "image" in product_data.keys():
            wanted_prod_data["image_URL"] = product_data["image"]
        else:
            wanted_prod_data["image_URL"] = product_data['@graph'][0]["image"]

        if "productID" in product_data.keys():
            price_endpoint = f"""{STARTER_ASOS_API}productIds={
                product_data['productID']
                }&store=COM&currency=GBP"""
        else:
            price_endpoint = f"""{STARTER_ASOS_API}productIds={
                product_data['@graph'][0]['productID']
                }&store=COM&currency=GBP"""

        price = requests.get(price_endpoint, timeout=5).json()[
            0]["productPrice"]["current"]["value"]

        sizes = requests.get(price_endpoint, timeout=5).json()[0]['variants']

        if price:
            wanted_prod_data["price"] = price
        else:
            wanted_prod_data["price"] = 0

        availabilities = []
        for size in sizes:
            if size["isInStock"] == True:
                availabilities.append(size["isInStock"])
            else:
                availabilities.append(size["isInStock"])

        if True in availabilities:
            wanted_prod_data["is_in_stock"] = True
        else:
            wanted_prod_data["is_in_stock"] = False

        return wanted_prod_data

    except AttributeError as error:
        return error


if __name__ == "__main__":

    load_dotenv()

    headers = {
        'user-agent': environ["USER_AGENT"]
    }
