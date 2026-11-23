# Tests for sgl.py
#
# These are integration tests: they run against the real MySQL database from .env,
# so the triggers and CHECK constraint in database.sql are tested too.
# Run database.sql first, then: pytest -v
#
# All test stays use room 101 and 202 in the year 2099, so they never clash with the
# example data. Every stay a test creates is deleted again afterwards.

from datetime import date

import mysql.connector
import pytest

from db import get_connection
from sql import OverlappedStays, PetStay, get_all_stays

ROOM_A = 1  # room 101, no example stays
ROOM_B = 4  # room 202, no example stays
BELLA = 1  # pet_id 1, owner Kari Nordmann
MAX = 3  # pet_id 3


@pytest.fixture(scope="session", autouse=True)
def database_available():
    """Skip every test if the database can't be reached."""
    try:
        get_connection().close()
    except Exception as err:
        pytest.skip(f"Could not connect to MySQL: {err}")


@pytest.fixture
def created():
    """Collects stay ids made during a test and deletes them afterwards."""
    ids = []
    yield ids
    conn = get_connection()
    cursor = conn.cursor()
    for stay_id in ids:
        cursor.execute("DELETE FROM stays WHERE stay_id = %s", (stay_id,))
    conn.commit()
    cursor.close()
    conn.close()


def make_stay(created, pet, room, check_in, check_out):
    """Adds a stay and remembers its id for cleanup."""
    stay = PetStay(pet, room, check_in, check_out)
    created.append(stay.add())
    return stay


# ---------- add() and get() ----------


def test_add_returns_id_and_sets_self_id(created):
    stay = make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))

    assert isinstance(stay.id, int)
    assert stay.id == created[0]


def test_get_returns_same_data_as_added(created):
    stay = make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))

    fetched = PetStay.get(stay.id)

    assert isinstance(fetched, PetStay)
    assert fetched.id == stay.id
    assert fetched.pet == BELLA
    assert fetched.room == ROOM_A
    assert fetched.check_in == date(2099, 1, 1)
    assert fetched.check_out == date(2099, 1, 5)


def test_get_unknown_id_returns_none():
    assert PetStay.get(999_999_999) is None


# ---------- insert trigger ----------


def test_add_overlapping_stay_raises(created):
    make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))

    with pytest.raises(OverlappedStays):
        make_stay(created, MAX, ROOM_A, date(2099, 1, 3), date(2099, 1, 8))


def test_add_back_to_back_stays_is_allowed(created):
    # Max checks in the same day Bella checks out
    make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))
    stay = make_stay(created, MAX, ROOM_A, date(2099, 1, 5), date(2099, 1, 8))

    assert stay.id is not None


def test_add_same_dates_in_other_room_is_allowed(created):
    make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))
    stay = make_stay(created, MAX, ROOM_B, date(2099, 1, 1), date(2099, 1, 5))

    assert stay.id is not None


# ---------- CHECK constraint ----------


def test_add_check_out_before_check_in_is_rejected(created):
    stay = PetStay(BELLA, ROOM_A, date(2099, 1, 5), date(2099, 1, 1))

    with pytest.raises(mysql.connector.Error) as err:
        created.append(stay.add())

    # It's the CHECK constraint failing, not the overlap trigger
    assert not isinstance(err.value, OverlappedStays)


# ---------- update() and update trigger ----------


def test_update_changes_the_row(created):
    stay = make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))

    stay.pet = MAX
    stay.room = ROOM_B
    stay.update()

    fetched = PetStay.get(stay.id)
    assert fetched.pet == MAX
    assert fetched.room == ROOM_B


def test_update_can_extend_own_stay(created):
    # The new dates overlap the stay's own old dates. This must not be blocked
    # (tests the "s.stay_id <> NEW.stay_id" line in the update trigger).
    stay = make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))

    stay.check_out = date(2099, 1, 7)
    stay.update()

    assert PetStay.get(stay.id).check_out == date(2099, 1, 7)


def test_update_into_other_stay_raises_and_keeps_old_values(created):
    make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))
    stay = make_stay(created, MAX, ROOM_A, date(2099, 1, 10), date(2099, 1, 15))

    stay.check_in = date(2099, 1, 3)
    with pytest.raises(OverlappedStays):
        stay.update()

    assert PetStay.get(stay.id).check_in == date(2099, 1, 10)


def test_update_moving_to_occupied_room_raises(created):
    make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))
    stay = make_stay(created, MAX, ROOM_B, date(2099, 1, 1), date(2099, 1, 5))

    stay.room = ROOM_A
    with pytest.raises(OverlappedStays):
        stay.update()


# ---------- delete() ----------


def test_delete_removes_the_stay(created):
    stay = make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))

    assert stay.delete() is True
    assert PetStay.get(stay.id) is None


def test_delete_unknown_id_returns_false():
    stay = PetStay(None, None, None, None, stay_id=999_999_999)

    assert stay.delete() is False


def test_deleted_room_dates_can_be_booked_again(created):
    stay = make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))
    stay.delete()

    new_stay = make_stay(created, MAX, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))
    assert new_stay.id is not None


# ---------- get_all_stays() ----------


def test_get_all_stays_includes_new_stay_with_names(created):
    stay = make_stay(created, BELLA, ROOM_A, date(2099, 1, 1), date(2099, 1, 5))

    rows = {row["stay_id"]: row for row in get_all_stays()}

    assert stay.id in rows
    row = rows[stay.id]
    assert row["pet_name"] == "Bella"
    assert row["owner_name"] == "Kari Nordmann"
    assert row["room_number"] == 101
