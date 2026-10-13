CREATE TABLE payment_statistic.receipt
(
    id                   SERIAL PRIMARY KEY,
    period TIMESTAMP NOT NULL,
    user_id              INTEGER       NOT NULL REFERENCES payment_statistic.users (id),
    qrraw                TEXT,
    retail_place         TEXT,
    retail_place_address TEXT,
    total_sum            NUMERIC(8, 2) NOT NULL,
    UNIQUE (user_id, qrraw)
);