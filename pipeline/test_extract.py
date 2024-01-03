"""
Tests the extraction file.
"""
import unittest
from unittest.mock import patch, MagicMock

from extract import get_domain_name, scrape_asos_page

EXAMPLE_HTML_TEXT = '''
<html><head><script>{"product_name":"Black Coat"}</script></head></html>'''
EXAMPLE_SOUP_STRING = '''
{"name":"Black Coat", "image": "http://asos.com/example_url", "productID": "123"}'''
EXAMPLE_ASOS_URL = 'http://asos.com/blackcoats'
ASOS_DOMAIN = 'asos.com'


class TestGetDomainName(unittest.TestCase):
    """
    Test class for the get_domain_name() function.
    """

    def test_get_domain_name(self):
        """
        Tests that get_domain_name functions as expected.
        """

        result = get_domain_name(EXAMPLE_ASOS_URL)

        self.assertEqual(result, ASOS_DOMAIN)

    def test_get_domain_name_string(self):
        """
        Tests that get_domain_name outputs a string.
        """

        result = get_domain_name(EXAMPLE_ASOS_URL)

        self.assertIsInstance(result, str)


class TestScrapeAsosPage(unittest.TestCase):
    """
    Test class for the scrape_asos_page() function.
    """
    @patch('extract.requests.get')
    @patch('extract.BeautifulSoup')
    @patch('extract.get_domain_name')
    def test_scrape_website(self, mock_get_domain_name, mock_beautiful_soup, mock_requests_get):
        """
        Tests that the web scraper functions as expected.
        """
        mock_page = MagicMock()
        mock_page.text = EXAMPLE_HTML_TEXT
        mock_requests_get.return_value = mock_page

        mock_soup = MagicMock()
        mock_soup.find.return_value.string = EXAMPLE_SOUP_STRING
        mock_beautiful_soup.return_value = mock_soup

        mock_get_domain_name.return_value = ASOS_DOMAIN

        result = scrape_asos_page(EXAMPLE_ASOS_URL, {'HeaderKey':'HeaderValue'})
        print(result)

        self.assertIn('Black Coat', result.get('product_name'))
        self.assertIn('http://asos.com/example_url', result.get('image_URL'))

    @patch('extract.requests.get')
    @patch('extract.BeautifulSoup')
    @patch('extract.get_domain_name')
    def test_scrape_website_returns_dict(
        self, mock_get_domain_name, mock_beautiful_soup, mock_requests_get
        ):
        """
        Tests that the web scraper function returns a dictionary.
        """
        mock_page = MagicMock()
        mock_page.text = EXAMPLE_HTML_TEXT
        mock_requests_get.return_value = mock_page

        mock_soup = MagicMock()
        mock_soup.find.return_value.string = EXAMPLE_SOUP_STRING
        mock_beautiful_soup.return_value = mock_soup

        mock_get_domain_name.return_value = ASOS_DOMAIN

        result = scrape_asos_page(EXAMPLE_ASOS_URL, {'HeaderKey':'HeaderValue'})

        self.assertIsInstance(result, dict)
