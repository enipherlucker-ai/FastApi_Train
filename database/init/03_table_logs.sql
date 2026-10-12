CREATE TABLE logs.api_logs
(
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES payment_statistic.users (id),
    method      TEXT NOT NULL,
    comment     TEXT,
    input_data  TEXT NOT NULL,
    output_data TEXT NOT NULL
) ;