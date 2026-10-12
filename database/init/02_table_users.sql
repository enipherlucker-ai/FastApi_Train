CREATE TABLE payment_statistic.users
(
    id          SERIAL PRIMARY KEY,
    name        TEXT    NOT NULL,
    age         INTEGER NOT NULL CHECK (age >= 0),
    description TEXT
);

INSERT INTO payment_statistic.users
    (id, name, age, description)
VALUES (20260408,
        'admin_user',
        18,
        'Административная УЗ');