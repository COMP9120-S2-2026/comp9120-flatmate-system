CREATE TABLE app_user (
    user_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone_num VARCHAR(20),
    email VARCHAR(255) NOT NULL UNIQUE,
    bio TEXT
);

CREATE TABLE property_characteristics (
    property_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    street_number VARCHAR(15) NOT NULL,
    street_name VARCHAR(100) NOT NULL,
    suburb VARCHAR(100) NOT NULL,
    state VARCHAR(3) NOT NULL CHECK (state IN('NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT')),
    postcode CHAR(4) NOT NULL CHECK (postcode ~ '^[0-9]{4}$'),
    unit_number VARCHAR(20),
    property_type VARCHAR(50) NOT NULL CHECK (property_type IN ('House', 'Apartment', 'Townhouse', 'Unit', 'Studio', 'Duplex')),
    total_rooms INTEGER NOT NULL CHECK (total_rooms > 0),
    car_spots INTEGER NOT NULL CHECK (car_spots >= 0),
    smoking_policy VARCHAR(30) CHECK(smoking_policy IN('No smoking', 'Outdoor only', 'Any')) NOT NULL,
    pet_friendly BOOLEAN NOT NULL,
    UNIQUE NULLS NOT DISTINCT (
        street_number,
        street_name,
        suburb,
        state,
        postcode,
        unit_number
    )
);

CREATE TABLE preference_profile (
    user_id INTEGER NOT NULL,
    profile_name VARCHAR(100) NOT NULL,
    min_rent NUMERIC(10,2) NOT NULL CHECK (min_rent >= 0),
    max_rent NUMERIC(10,2) NOT NULL CHECK (max_rent >= min_rent),
    desired_move_in_date DATE,
    smoking_preference VARCHAR(30) CHECK(smoking_preference IN('No smoking', 'Outdoor only', 'Any')) NOT NULL,
    pet_friendly BOOLEAN,
    PRIMARY KEY (user_id, profile_name),
    FOREIGN KEY (user_id) REFERENCES app_user(user_id)
);

CREATE TABLE preferred_suburb (
    user_id INTEGER NOT NULL,
    profile_name VARCHAR(100) NOT NULL,
    preferred_suburb VARCHAR(100) NOT NULL,
    PRIMARY KEY (
        user_id,
        profile_name,
        preferred_suburb
    ),
    FOREIGN KEY (user_id, profile_name) REFERENCES preference_profile(user_id, profile_name)
);

CREATE TABLE room (
    room_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_type VARCHAR(50) NOT NULL CHECK (room_type IN ('Private', 'Shared')),
    num_roommates INTEGER NOT NULL CHECK (num_roommates >= 0),
    is_furnished BOOLEAN NOT NULL,
    has_ensuite BOOLEAN NOT NULL,
    description TEXT,
    property_id INTEGER NOT NULL,
    FOREIGN KEY (property_id) REFERENCES property_characteristics(property_id)
);

CREATE TABLE listing (
    listing_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id INTEGER NOT NULL,
    creator_user_id INTEGER NOT NULL,
    weekly_rent NUMERIC(10,2) NOT NULL CHECK (weekly_rent > 0),
    available_from DATE NOT NULL,
    listing_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL CHECK(status IN('OPEN', 'PAUSED', 'CLOSED')),
    num_housemates INTEGER NOT NULL CHECK (num_housemates >= 0),
    FOREIGN KEY (room_id) REFERENCES room(room_id),
    FOREIGN KEY (creator_user_id) REFERENCES app_user(user_id)    
);

CREATE TABLE saves (
    user_id INTEGER NOT NULL,
    listing_id INTEGER NOT NULL,
    preference_rank INTEGER CHECK (preference_rank > 0),
    PRIMARY KEY (user_id, listing_id),
    FOREIGN KEY (user_id) REFERENCES app_user(user_id),
    FOREIGN KEY (listing_id) REFERENCES listing(listing_id), 
    UNIQUE (user_id, preference_rank)
);

CREATE TABLE application (
    application_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL,
    listing_id INTEGER NOT NULL,
    application_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(30) NOT NULL CHECK(status IN('PENDING', 'ACCEPTED', 'REJECTED')) DEFAULT 'PENDING', 
    message TEXT,
    FOREIGN KEY (user_id) REFERENCES app_user(user_id),
    FOREIGN KEY (listing_id) REFERENCES listing(listing_id), 
	UNIQUE(user_id, listing_id)
);

CREATE TABLE viewing_slot (
    listing_id INTEGER NOT NULL,
    viewing_timestamp TIMESTAMP NOT NULL,
    status VARCHAR(30) NOT NULL CHECK(status IN('AVAILABLE', 'BOOKED', 'CANCELLED')) DEFAULT 'AVAILABLE',
    PRIMARY KEY (listing_id, viewing_timestamp),
    FOREIGN KEY (listing_id) REFERENCES listing(listing_id)
);

CREATE TABLE viewing_booking (
    booking_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL,
    listing_id INTEGER NOT NULL,
    viewing_timestamp TIMESTAMP NOT NULL,
    booking_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(30) NOT NULL CHECK (status IN('CONFIRMED', 'CANCELLED')) DEFAULT 'CONFIRMED',
    FOREIGN KEY (user_id) REFERENCES app_user(user_id),
    FOREIGN KEY (listing_id, viewing_timestamp) REFERENCES viewing_slot(listing_id, viewing_timestamp)
);