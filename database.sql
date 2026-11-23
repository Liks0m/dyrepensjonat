DROP DATABASE IF EXISTS dyrepensjonat;
CREATE DATABASE dyrepensjonat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dyrepensjonat;

CREATE TABLE owners
(
    owner_id INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    name     VARCHAR(100)                   NOT NULL,
    phone    VARCHAR(20) UNIQUE             NOT NULL,
    email    VARCHAR(120) UNIQUE            NOT NULL
);

CREATE TABLE pets
(
    pet_id   INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    owner_id INT                            NOT NULL,
    name     VARCHAR(80)                    NOT NULL,
    species  VARCHAR(40)                    NOT NULL,
    breed    VARCHAR(80),
    CONSTRAINT fk_owner_id FOREIGN KEY (owner_id) REFERENCES owners (owner_id) ON DELETE CASCADE
);

CREATE TABLE rooms
(
    room_id     INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    room_number INT                            NOT NULL,
    room_type   VARCHAR(40)                    NOT NULL,
    daily_rate  DECIMAL(8, 2)                  NOT NULL CHECK (daily_rate >= 0)
);

CREATE TABLE stays
(
    stay_id   INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    pet_id    INT                            NOT NULL,
    room_id   INT                            NOT NULL,
    check_in  DATE                           NOT NULL,
    check_out DATE                           NOT NULL,
    CONSTRAINT chk_no_reverse_dates CHECK (check_out > check_in),
    CONSTRAINT fk_pet_id FOREIGN KEY (pet_id) REFERENCES pets (pet_id) ON DELETE CASCADE,
    CONSTRAINT fk_room_id FOREIGN KEY (room_id) REFERENCES rooms (room_id) ON DELETE CASCADE
);


CREATE TRIGGER trg_stays_no_overlap_insert
    BEFORE INSERT
    ON stays -- runs automatically before a new stay is saved
    FOR EACH ROW
BEGIN
    -- NEW = the row being inserted, s = stays already in the table
    IF EXISTS (SELECT 1
               FROM stays s
               WHERE s.room_id = NEW.room_id    -- same room
                 AND s.check_in < NEW.check_out -- existing stay starts before the new one ends
                 AND NEW.check_in < s.check_out -- new stay starts before the existing one ends
    ) THEN
        SIGNAL SQLSTATE '45000' -- raise an error, so the INSERT is cancelled
            SET MESSAGE_TEXT = 'Room is already occupied in this period';
    END IF;
END;


-- ---------- Example data ----------

INSERT INTO owners (name, phone, email)
VALUES ('Kari Nordmann', '91234567', 'kari.nordmann@example.com'),     -- owner_id 1
       ('Ola Hansen', '92345678', 'ola.hansen@example.com'),           -- owner_id 2
       ('Ingrid Johansen', '41234567', 'ingrid.johansen@example.com'), -- owner_id 3
       ('Lars Berg', '47654321', 'lars.berg@example.com'),             -- owner_id 4
       ('Sofie Larsen', '98765432', 'sofie.larsen@example.com'); -- owner_id 5

INSERT INTO pets (owner_id, name, species, breed)
VALUES (1, 'Bella', 'Hund', 'Labrador retriever'), -- pet_id 1
       (2, 'Pus', 'Katt', 'Norsk skogkatt'),       -- pet_id 2
       (3, 'Max', 'Hund', 'Border collie'),        -- pet_id 3
       (4, 'Luna', 'Kanin', 'Dvergvedder'),        -- pet_id 4
       (5, 'Simba', 'Katt', NULL); -- pet_id 5, mixed breed / unknown

INSERT INTO rooms (room_number, room_type, daily_rate)
VALUES (101, 'Liten hund', 350.00), -- room_id 1
       (102, 'Stor hund', 450.00),  -- room_id 2
       (201, 'Katterom', 300.00),   -- room_id 3
       (202, 'Katterom', 300.00),   -- room_id 4
       (301, 'Smådyr', 200.00); -- room_id 5

INSERT INTO stays (pet_id, room_id, check_in, check_out)
VALUES (1, 2, '2026-06-28', '2026-07-05'), -- Bella, summer holiday
       (3, 2, '2026-07-05', '2026-07-12'), -- Max, same room, checks in the day Bella leaves
       (2, 3, '2026-07-01', '2026-07-14'), -- Pus in the cat room
       (4, 5, '2026-10-10', '2026-10-13'), -- Luna, autumn break
       (1, 2, '2026-12-22', '2026-12-27'); -- Bella again, Christmas

CREATE USER IF NOT EXISTS 'dp_app'@'%' IDENTIFIED BY 'gokstad-password123';
GRANT SELECT, INSERT, UPDATE, DELETE ON dyrepensjonat.* TO 'dp_app'@'%';

SHOW GRANTS FOR 'dp_app'@'%';