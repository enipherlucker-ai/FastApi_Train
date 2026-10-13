CREATE TABLE payment_statistic.receipt_compound
(
    id         SERIAL PRIMARY KEY,
    name       TEXT           NOT NULL,
    receipt_id INTEGER        NOT NULL REFERENCES payment_statistic.receipt (id),
    user_id    INTEGER        NOT NULL REFERENCES payment_statistic.users (id),
    group_id   INTEGER        NOT NULL REFERENCES payment_statistic.groups (id),
    vat        INTEGER        NOT NULL,
    vat_sum    NUMERIC(8, 2)  NOT NULL,
    price      NUMERIC(8, 2)  NOT NULL,
    quantity   NUMERIC(10, 3) NOT NULL,
    sum        NUMERIC(8, 2)  NOT NULL
);