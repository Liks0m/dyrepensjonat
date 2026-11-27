# This is the only file that talks to the database

import mysql.connector
from mysql.connector import errorcode

from db import get_connection


class OverlappedStays(Exception):
    """Raised when a room is already booked for the requested dates."""


def get_all_stays():
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                SELECT s.stay_id,
                       s.check_in,
                       s.check_out,
                       p.name as pet_name,
                       p.pet_id,
                       p.breed,
                       p.species,
                       o.name as owner_name,
                       o.owner_id,
                       r.room_number,
                       r.room_type,
                       r.room_id
                FROM stays AS s
                    INNER JOIN pets AS p ON p.pet_id = s.pet_id
                    INNER JOIN rooms AS r ON r.room_id = s.room_id
                    INNER JOIN owners AS o ON o.owner_id = p.owner_id
                    """)
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def get_all_pets():
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                SELECT p.pet_id, p.name, p.species, o.name AS owner_name
                FROM pets AS p
                INNER JOIN owners AS o ON o.owner_id = p.owner_id
                ORDER BY p.name;
                """)
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def get_all_rooms():
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
               SELECT room_id, room_number, room_type, daily_rate
               FROM rooms
               ORDER BY room_number;             
                """)
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


class PetStay:
    def __init__(self, pet_id, room_id, check_in, check_out, stay_id=None):
        self.id = stay_id
        self.pet = pet_id
        self.room = room_id
        self.check_in = check_in
        self.check_out = check_out

    def add(self):
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO stays(pet_id, room_id, check_in, check_out)
                VALUES (%s, %s, %s, %s)
                        """,
                (self.pet, self.room, self.check_in, self.check_out),
            )
            conn.commit()
            self.id = cursor.lastrowid
            return cursor.lastrowid
        except mysql.connector.Error as err:
            conn.rollback()
            if err.errno == errorcode.ER_SIGNAL_EXCEPTION:
                raise OverlappedStays(
                    f"The room requested by owner is already booked for the dates {self.check_in} to {self.check_out}"
                ) from err
            raise
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @classmethod
    def get(cls, stay_id):
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT * 
                FROM stays
                WHERE stay_id = %s
            """,
                (stay_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return cls(
                row["pet_id"],
                row["room_id"],
                row["check_in"],
                row["check_out"],
                stay_id=row["stay_id"],
            )
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def update(self):
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE stays
                SET pet_id = %s, room_id = %s, check_in = %s, check_out = %s
                WHERE stay_id = %s
            """,
                (self.pet, self.room, self.check_in, self.check_out, self.id),
            )
            conn.commit()
        except mysql.connector.Error as err:
            conn.rollback()
            if err.errno == errorcode.ER_SIGNAL_EXCEPTION:
                raise OverlappedStays(
                    f"The room user requested is already booked for the dates {self.check_in} to {self.check_out}"
                ) from err
            raise

        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def delete(self):
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stays WHERE stay_id = %s ", (self.id,))
            conn.commit()
            return cursor.rowcount == 1
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()
