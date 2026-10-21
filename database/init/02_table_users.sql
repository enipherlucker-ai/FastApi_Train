CREATE TABLE payment_statistic.users
(
    id            SERIAL PRIMARY KEY,
    name          TEXT    NOT NULL,
    age           INTEGER NOT NULL CHECK (age >= 0),
    description   TEXT,
    login         TEXT UNIQUE,
    password_hash TEXT
);



INSERT INTO payment_statistic.users
    (id, name, age, description, login, password_hash)
VALUES (20260308,
        'admin_user',
        18,
        'Административная УЗ',
        NULL,
        NULL);