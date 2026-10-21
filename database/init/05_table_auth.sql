CREATE TABLE payment_statistic.user_sessions
(
    id         SERIAL PRIMARY KEY,
    token_hash TEXT        NOT NULL UNIQUE,
    user_id    INTEGER     NOT NULL REFERENCES payment_statistic.users (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);