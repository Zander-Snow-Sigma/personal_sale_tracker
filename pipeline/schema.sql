DROP TABLE IF EXISTS prices;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255),
    product_url TEXT NOT NULL,
    website_name VARCHAR(255) NOT NULL,
    image_url TEXT
);

CREATE TABLE prices (
    price_id SERIAL PRIMARY KEY,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    price DECIMAL NOT NULL,
    product_id INT
);

CREATE TABLE  users (
    user_id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL
);

CREATE TABLE  subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    user_id INT,
    product_id INT
);

ALTER TABLE prices
ADD CONSTRAINT product_fk
FOREIGN KEY (product_id)
REFERENCES products(product_id);

ALTER TABLE subscriptions
ADD CONSTRAINT user_fk
FOREIGN KEY (user_id)
REFERENCES users(user_id);

ALTER TABLE products 
ADD CONSTRAINT product_sub_fk
FOREIGN KEY (product_id)
REFERENCES products(product_id);

COMMIT;