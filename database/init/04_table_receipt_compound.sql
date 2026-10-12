CREATE TABLE payment_statistic.receipt_compound
(
    receipt_id INTEGER NOT NULL REFERENCES payment_statistic.receipt (id),
    user_id    INTEGER NOT NULL REFERENCES payment_statistic.users (id),
    vat        FLOAT   NOT NULL,
    vat_sum    FLOAT   NOT NULL,
    price      FLOAT   NOT NULL,
    quantity   INTEGER NOT NULL,
    sum        FLOAT   NOT NULL,
    primary key (receipt_id, user_id)
);