### update_price_and_send_alerts.py

This script is triggered every 3 minutes. It updates the price of every item in the database
and sends alerts to the subscribers of each product in the following cases:

    - The product was out of stock and has gone back in stock.
    - The product was in stock and has now gone out of stock.
    - The product has decreased in price. 


#### Required environment variables:

USER_AGENT
DB_USER
DB_PASSWORD
DB_PORT
DB_HOST
DB_NAME
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
SENDER_EMAIL_ADDRESS