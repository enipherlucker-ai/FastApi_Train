CREATE TABLE payment_statistic.users
(
    id          SERIAL PRIMARY KEY,
    name        TEXT    NOT NULL,
    age         INTEGER NOT NULL CHECK (age >= 0),
    description TEXT
);