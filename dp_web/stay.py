import datetime as dt

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

import db_link

bp = Blueprint("stay", __name__)


class StayHTTPRequest:
    def __init__(self, pet_id, room_id, check_in, check_out):
        self.pet = pet_id
        self.room = room_id
        self.check_in = check_in
        self.check_out = check_out

    @classmethod
    def from_form(cls, form):
        return cls(
            form.get("pet_id", type=int),
            form.get("room_id", type=int),
            form.get("check_in"),
            form.get("check_out"),
        )


# R: Read


@bp.route("/stay")
def stay_read():
    return render_template(
        "stay.html",
        stays=db_link.get_all_stays(),
    )


# C: Create


@bp.route("/stay/new", methods=["GET", "POST"], endpoint="stay_create")
def stay_create():
    if request.method == "POST":
        # Read what the browser sent; the names match name="..." in stay_form.html
        form = StayHTTPRequest.from_form(request.form)
        # After this check ty knows every value is set (not None)
        if not (form.pet and form.room and form.check_in and form.check_out):
            abort(400, "All fields are required.")

        try:
            check_in = dt.date.fromisoformat(form.check_in)
            check_out = dt.date.fromisoformat(form.check_out)
        except ValueError:
            abort(400, "Dates must be in the format YYYY-MM-DD.")

        if check_out <= check_in:
            flash("Check-out must be after check-in.", "error")
        else:
            # Build the object with the values, then save it
            stay = db_link.PetStay(form.pet, form.room, form.check_in, form.check_out)
            try:
                stay.add()
            except db_link.OverlappedStays as err:
                flash(str(err), "error")  # room already booked, show the form again
            else:
                flash(f"Stay #{stay.id} was added.", "success")
                # Redirect so refreshing the page doesn't add the stay twice
                return redirect(url_for("stay.stay_read"))

    # GET, or a POST that failed: show the form (it keeps what the user typed)
    return render_template(
        "stay_form.html",
        pets=db_link.get_all_pets(),
        rooms=db_link.get_all_rooms(),
    )


# U: Update


@bp.route("/stay/<int:stay_id>/edit", methods=["GET", "POST"], endpoint="stay_edit")
def stay_update(stay_id):
    stay = db_link.PetStay.get(stay_id)
    if stay is None:
        abort(404)
    if request.method == "POST":
        # Read what the browser sent; the names match name="..." in stay_form.html
        form = StayHTTPRequest.from_form(request.form)
        # After this check ty knows every value is set (not None)
        if not (form.pet and form.room and form.check_in and form.check_out):
            abort(400, "All fields are required.")

        try:
            check_in = dt.date.fromisoformat(form.check_in)
            check_out = dt.date.fromisoformat(form.check_out)
        except ValueError:
            abort(400, "Dates must be in the format YYYY-MM-DD.")

        if check_out <= check_in:
            flash("Check-out must be after check-in.", "error")
        else:
            # Build the object with the values, then save it
            stay = db_link.PetStay(
                form.pet, form.room, form.check_in, form.check_out, stay_id
            )
            try:
                stay.update()
            except db_link.OverlappedStays as err:
                flash(str(err), "error")  # room already booked, show the form again
            else:
                flash(f"Stay #{stay.id} was updated.", "success")
                # Redirect so refreshing the page doesn't add the stay twice
                return redirect(url_for("stay.stay_read"))

    return render_template(
        "stay_form.html",
        edit_stay=stay,
        pets=db_link.get_all_pets(),
        rooms=db_link.get_all_rooms(),
    )


# D: Delete
@bp.route("/stay/<int:stay_id>/delete", methods=["POST"], endpoint="stay_delete")
def stay_delete(stay_id):
    stay = db_link.PetStay.get(stay_id)
    if stay is None or not db_link.PetStay.delete(stay):
        abort(404)
    flash(f"Stay #{stay.id} was updated.", "success")
    # Redirect so refreshing the page doesn't add the stay twice
    return redirect(url_for("stay.stay_read"))
