CREATE TABLE logs.api_logs
(
    id      SERIAL PRIMARY KEY,
    id_user INTEGER REFERENCES payment_statistic.users (id),
    service TEXT NOT NULL,
    method  TEXT NOT NULL,
    comment TEXT,
    input   TEXT NOT NULL,
    output  TEXT NOT NULL
) ;