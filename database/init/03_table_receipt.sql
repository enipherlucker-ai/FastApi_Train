CREATE TABLE payment_statistic.receipt
(
    id                   SERIAL PRIMARY KEY,
    period               TIMESTAMP NOT NULL,
    id_user              INTEGER NOT NULL REFERENCES payment_statistic.users (id),
    qrraw                TEXT,
    retail_place         TEXT,
    retail_place_address TEXT,
    total_sum            FLOAT NOT NULL
);