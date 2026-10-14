-- Integration scaffold only. Member C owns accounts and authentication.
-- Keep these identifiers and columns when extending this table.
CREATE TABLE app_user (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name TEXT NOT NULL CHECK (btrim(first_name) <> ''),
    last_name TEXT NOT NULL CHECK (btrim(last_name) <> ''),
    email TEXT NOT NULL UNIQUE,
    phone_num TEXT,
    bio TEXT
);
