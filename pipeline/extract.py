"""Extracts/Scrapes the desired information from the required product."""
from os import environ
from urllib.request import urlopen

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests as req


def scrape_product_page(link: str, headers: dict) -> dict:
    """Returns a dict of scraped details for a specific product."""

    res = req.get(link, headers=headers, timeout=5)
    soup = BeautifulSoup(res.content, features="html.parser")
    price = soup.find_all('price-screenreader-only-text')
    print(price)

    product_price_element = soup.find(
        'span', {'data-testid': 'price-screenreader-only-text'})
    product = {
        "name": soup.find("h1", class_="jcdpl").text.strip(),
        "price":  product_price_element}

    return product


def get_html(url):
    """gets html from webpage"""
    page = urlopen(url)
    html_bytes = page.read()
    html = html_bytes.decode("utf_8")
    return html


if __name__ == "__main__":

    load_dotenv()

    headers = {
        'authority':  environ["AUTHORITY"],
        'user-agent': environ["USER_AGENT"],
    }

    product_page = scrape_product_page(
        "https://www.asos.com/asos-design/asos-design-chiffon-bias-maxi-skirt-in-leopard-print/prd/205497720#colourWayId-205497727", headers)

    print(product_page)
