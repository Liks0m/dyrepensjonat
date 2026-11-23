# Constraining a pet to exactly one owner (MySQL)

## Each pet has exactly one owner (an owner can have many pets)

Put a single `owner_id` column on `pets`, make it `NOT NULL`, and add a
`FOREIGN KEY` that references `owners`:

```sql
CREATE TABLE pets
(
    pet_id   INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    owner_id INT                            NOT NULL,
    name     VARCHAR(100)                   NOT NULL,
    species  VARCHAR(50)                    NOT NULL,
    CONSTRAINT fk_pets_owner
        FOREIGN KEY (owner_id) REFERENCES owners (owner_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
```

What each part does:

- **One column, one value:** a row in `pets` has only one `owner_id` field, so a
  pet can't have two owners.
- **`NOT NULL`:** every pet must have an owner.
- **`FOREIGN KEY ... REFERENCES owners(owner_id)`:** the owner has to exist in
  `owners`. If you try to insert a pet with an `owner_id` that isn't there, the
  insert fails.
- **`ON DELETE RESTRICT`:** you can't delete an owner who still has pets.
  (Use `ON DELETE CASCADE` if deleting the owner should delete their pets too.)

## One owner can only have one pet (strict one-to-one)

If the rule is also that an owner can't have more than one pet, add `UNIQUE`
to `owner_id`:

```sql
    owner_id INT NOT NULL UNIQUE,
```

or as a named constraint:

```sql
    CONSTRAINT uq_pets_owner UNIQUE (owner_id),
```

## Test it

```sql
INSERT INTO owners (name, phone, email) VALUES ('Kari', '12345678', 'kari@example.com');

INSERT INTO pets (owner_id, name, species) VALUES (1, 'Fido', 'Hund');   -- OK
INSERT INTO pets (owner_id, name, species) VALUES (99, 'Pus', 'Katt');   -- Fails: owner 99 doesn't exist (FK)
INSERT INTO pets (owner_id, name, species) VALUES (NULL, 'Bob', 'Hund'); -- Fails: NOT NULL
INSERT INTO pets (owner_id, name, species) VALUES (1, 'Rex', 'Hund');    -- Fails only if UNIQUE (one-to-one) is added
```

## Note about the current `database.sql`

The `pets` table there ends with a trailing comma (`owner_id INT NOT NULL,`)
followed by `)`, which is a syntax error in MySQL. It also has no foreign key
yet, so right now nothing stops a pet from pointing to an owner that doesn't
exist.

## Follow-up: "an owner can have many pets, but a pet only one owner"

This is the first example above (one-to-many), with no `UNIQUE` on `owner_id`.

- **A pet only gets one owner** because `owner_id` is a single column on the
  pet's row, and each row can hold only one value there.
- **An owner can have many pets** because nothing stops several pet rows from
  having the same `owner_id`.

```
owners                 pets
owner_id | name        pet_id | owner_id | name
---------+------       -------+----------+------
1        | Kari        1      | 1        | Fido   <- Kari
2        | Ola         2      | 1        | Rex    <- Kari (same owner, OK)
                       3      | 2        | Pus    <- Ola
```

You can't give Fido a second owner, because there's nowhere to put one.

What would break the rule is a link table (e.g. `pet_owners(pet_id, owner_id)`)
with no constraint, because then one pet could have many rows. If you ever use
a link table anyway, add `UNIQUE (pet_id)` to it so each pet still appears
only once.

## Review: `owners` / `pets` without a PRIMARY KEY

Proposed version:

```sql
CREATE TABLE owners
(
    owner_id INT AUTO_INCREMENT UNIQUE NOT NULL,
    name     VARCHAR(100)              NOT NULL,
    phone    VARCHAR(20) UNIQUE        NOT NULL,
    email    VARCHAR(120) UNIQUE       NOT NULL
);

CREATE TABLE pets
(
    pet_id   INT AUTO_INCREMENT        NOT NULL,
    owner_id INT UNIQUE  NOT NULL,
    name     VARCHAR(80) NOT NULL,
    species  VARCHAR(40) NOT NULL,
    breed    VARCHAR(80) NOT NULL,
    CONSTRAINT fk_owner_id FOREIGN KEY (owner_id) REFERENCES owners (owner_id) ON DELETE CASCADE
);
```

Problems:

1. **`UNIQUE` on `pets.owner_id` breaks the rule you want.** It means each
   owner can only have one pet, which makes it one-to-one. Remove `UNIQUE`
   so an owner can have many pets while each pet still has one owner.
2. **`pets` won't be created.** In MySQL an `AUTO_INCREMENT` column has to be
   a key. `pet_id` has no `PRIMARY KEY` or `UNIQUE`, so you get
   `ERROR 1075: Incorrect table definition; there can be only one auto column and it must be defined as a key`.
   (`owners` is fine, because its `owner_id` has `UNIQUE`.)
3. **"No primary key" doesn't really work.** An ER model normally marks a
   key attribute (the underlined one) for each entity, and that becomes the
   primary key in the table. `UNIQUE NOT NULL` does almost the same thing; InnoDB
   even uses the first `UNIQUE NOT NULL` column as the table's clustered index
   if there's no primary key. So you'd effectively have a primary key under
   another name. Using `PRIMARY KEY` is clearer and is what an examiner expects.
   If your ER diagram has no keys, check whether it just doesn't show them.
4. Small points:
   - `breed NOT NULL` forces a value even for mixed breeds or unknowns. Consider
     allowing `NULL`.
   - `ON DELETE CASCADE` deletes an owner's pets when you delete the owner,
     and any `stays` that cascade from pets as well. That's fine if it's on
     purpose. Otherwise use `RESTRICT`.

Suggested version:

```sql
CREATE TABLE owners
(
    owner_id INT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(100)        NOT NULL,
    phone    VARCHAR(20)  UNIQUE NOT NULL,
    email    VARCHAR(120) UNIQUE NOT NULL
);

CREATE TABLE pets
(
    pet_id   INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT         NOT NULL,          -- no UNIQUE: one owner, many pets
    name     VARCHAR(80) NOT NULL,
    species  VARCHAR(40) NOT NULL,
    breed    VARCHAR(80),
    CONSTRAINT fk_pets_owner FOREIGN KEY (owner_id)
        REFERENCES owners (owner_id) ON DELETE CASCADE
);
```

If you really must leave out `PRIMARY KEY`, at least use
`pet_id INT AUTO_INCREMENT UNIQUE NOT NULL` so the table can be created.

## Data integrity check of `database.sql` against the business rules

| # | Business rule | Enforced? | How / why not |
|---|---------------|-----------|---------------|
| 1 | An owner can register one or more pets | Yes (mostly) | `pets.owner_id` has no `UNIQUE`, so many pets can share an owner. "At least one" can't be enforced with constraints, and an owner has to exist before their first pet anyway. That's normal and acceptable. |
| 2 | A pet belongs to one owner | Yes | `pets.owner_id INT NOT NULL` with an FK to `owners`. One column means one owner, `NOT NULL` means it's required, and the FK means the owner must exist. |
| 3 | A pet can have multiple stays, each visit is a separate stay | Yes | `stays.pet_id` has no `UNIQUE`, and every visit is its own row with its own `stay_id`. |
| 4 | Each stay involves one pet and one room | Yes | `stays.pet_id` and `stays.room_id` are both `NOT NULL` FKs, one column each. |
| 5 | A room can be used for many stays, but not by two pets at the same time | **No** | `room_id` isn't unique, so a room can have many stays. But nothing stops two stays in the same room from overlapping in dates. |

### Gaps that weaken rule 5

1. **No overlap check.** These two rows are both accepted today:
   ```sql
   INSERT INTO stays (pet_id, room_id, check_in, check_out) VALUES (1, 1, '2026-12-01', '2026-12-10');
   INSERT INTO stays (pet_id, room_id, check_in, check_out) VALUES (2, 1, '2026-12-05', '2026-12-08'); -- same room, overlapping
   ```
   MySQL has no "exclusion constraint", so you need triggers (see below).
2. **No check that `check_out` comes after `check_in`.** A stay from `2026-12-10` to
   `2026-12-01` is accepted, and backwards dates would also slip past an
   overlap check. Add:
   ```sql
   CONSTRAINT chk_dates CHECK (check_out > check_in)
   ```
   (Use `>=` if a same-day stay is allowed.) `CHECK` is enforced in MySQL 8.0.16+.
3. **`rooms.room_number` isn't `UNIQUE`.** Two rows could both be "room 101",
   each with its own `room_id`, and the overlap check would treat them as
   different rooms. Add `UNIQUE` to `room_number`.

### Trigger that enforces rule 5

Two stays overlap when `existing.check_in < new.check_out AND new.check_in < existing.check_out`.
That means a pet can check in on the same day the previous pet checks out.

```sql
DELIMITER //

CREATE TRIGGER trg_stays_no_overlap_insert
BEFORE INSERT ON stays
FOR EACH ROW
BEGIN
    IF EXISTS (SELECT 1
               FROM stays s
               WHERE s.room_id = NEW.room_id
                 AND s.check_in < NEW.check_out
                 AND NEW.check_in < s.check_out) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Room is already occupied in this period';
    END IF;
END//

CREATE TRIGGER trg_stays_no_overlap_update
BEFORE UPDATE ON stays
FOR EACH ROW
BEGIN
    IF EXISTS (SELECT 1
               FROM stays s
               WHERE s.room_id = NEW.room_id
                 AND s.stay_id <> NEW.stay_id      -- don't compare the row with itself
                 AND s.check_in < NEW.check_out
                 AND NEW.check_in < s.check_out) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Room is already occupied in this period';
    END IF;
END//

DELIMITER ;
```

(Optional: the rules don't say so, but the same pet logically can't be in two
rooms at once. The same trigger with `s.pet_id = NEW.pet_id` would block that.)

### Other remarks (not rule violations)

- **`ON DELETE CASCADE` on `fk_room_id`:** deleting a room deletes its whole
  stay history, and deleting an owner removes their pets and all their stays.
  For a boarding business you usually want to keep history, so consider
  `ON DELETE RESTRICT`, at least for rooms.
- **`DROP TABLE IF EXISTS ...` after `DROP DATABASE`** never does anything,
  because the database was just recreated empty. It's harmless.
- **`PRIMARY KEY NOT NULL`:** the `NOT NULL` is redundant, since a primary key
  is always `NOT NULL`. It's harmless.

### Summary

Rules 1–4 are met by the primary keys, the `NOT NULL` foreign keys, and the lack
of `UNIQUE` on the "many" side. Rule 5 is **not** met. To fix it, add
`CHECK (check_out > check_in)`, add `UNIQUE` to `room_number`, and add the two
overlap triggers.

## Point 1 explained in SQL: the overlap trigger, step by step

```sql
-- MySQL normally ends a statement at ';'. The trigger body contains ';',
-- so we temporarily make '//' the statement terminator.
DELIMITER //

-- A trigger is code MySQL runs automatically.
-- BEFORE INSERT: it runs before the new row is saved, so we can still stop it.
CREATE TRIGGER trg_stays_no_overlap_insert
BEFORE INSERT ON stays
FOR EACH ROW                -- runs once per row being inserted
BEGIN
    -- NEW = the row someone is trying to insert.
    -- s   = rows that are already in the stays table.
    IF EXISTS (
        SELECT 1
        FROM stays s
        WHERE s.room_id = NEW.room_id           -- same room
          AND s.check_in < NEW.check_out        -- existing stay starts before the new one ends
          AND NEW.check_in < s.check_out        -- new stay starts before the existing one ends
    ) THEN
        -- If any such row exists, the dates overlap: abort the INSERT with an error.
        SIGNAL SQLSTATE '45000'                 -- '45000' = user-defined error
            SET MESSAGE_TEXT = 'Room is already occupied in this period';
    END IF;
    -- If no row matched, the trigger ends and the INSERT goes through.
END//

DELIMITER ;
```

### Why the two date conditions find every overlap

Two periods overlap exactly when **each starts before the other ends**:

```
existing:      |------------|            check_in 1 dec, check_out 10 dec
new (overlap):        |---------|        5 dec – 12 dec  -> 1<12 and 5<10  -> blocked
new (inside):     |----|                 3 dec – 6 dec   -> 1<6  and 3<10  -> blocked
new (after):                 |------|    10 dec – 15 dec -> 1<15 but 10<10 is false -> allowed
new (before): |--|                       25 nov – 1 dec  -> 1<1 is false   -> allowed
```

Because the comparisons use `<` (not `<=`), a new pet can check in on the same
day the previous one checks out.

### Trying it out

```sql
INSERT INTO stays (pet_id, room_id, check_in, check_out)
VALUES (1, 1, '2026-12-01', '2026-12-10');   -- OK, room 1 is empty

INSERT INTO stays (pet_id, room_id, check_in, check_out)
VALUES (2, 1, '2026-12-05', '2026-12-08');   -- ERROR 1644 (45000): Room is already occupied in this period

INSERT INTO stays (pet_id, room_id, check_in, check_out)
VALUES (2, 1, '2026-12-10', '2026-12-15');   -- OK, starts the day the first stay ends

INSERT INTO stays (pet_id, room_id, check_in, check_out)
VALUES (2, 2, '2026-12-05', '2026-12-08');   -- OK, different room
```

### The UPDATE version

`INSERT` isn't the only way to create an overlap. Someone could also `UPDATE` an
existing stay's dates or room. The `BEFORE UPDATE` trigger has the same check
plus one extra line:

```sql
  AND s.stay_id <> NEW.stay_id   -- skip the row being updated, or it would "overlap" with itself
```

## Is the trigger code MySQL?

Yes. `CREATE TRIGGER ... BEFORE INSERT ... FOR EACH ROW`, `NEW.column`,
`IF EXISTS (...) THEN ... END IF;`, and `SIGNAL SQLSTATE '45000'` are all MySQL
(5.5+ / 8.x) syntax. In PostgreSQL, a trigger has to call a separate function
instead.

`DELIMITER` is the one exception. It isn't SQL. It's a command for the `mysql`
command-line client and MySQL Workbench, telling them where the trigger
statement ends.
- `mysql` CLI / MySQL Workbench / `source database.sql`: keep `DELIMITER`.
- Some other tools (e.g. DataGrip, phpMyAdmin's SQL box, many drivers) split
  statements differently and may reject `DELIMITER`. There, leave it out and run the
  `CREATE TRIGGER ... END` block as a single statement.

## Example data added to `database.sql`

Five realistic rows per table were added at the end of `database.sql`, after the
trigger, so the trigger checks the example stays too. The ID columns are left
out and AUTO_INCREMENT numbers them 1–5 in insert order. That's always true
because the script drops and recreates the database. The foreign keys use those numbers.

How the data fits the business rules:
- Every owner has a pet (5 owners, 5 pets).
- Bella has two separate stays, so a pet can have multiple stays.
- Every stay has exactly one valid `pet_id` and `room_id`.
- Room 102 is used three times with no overlap. Max checks in on the day
  Bella checks out, which the trigger allows because it compares with `<`.
- Room types match the species. Simba's breed is `NULL` (mixed or unknown).
- Simba and rooms 101 and 202 have no stays, which is allowed.
