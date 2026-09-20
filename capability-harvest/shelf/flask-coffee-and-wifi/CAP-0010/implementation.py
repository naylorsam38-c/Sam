# Harvested by harvest_parts.py
# capability : CAP-0010 (add favourite)
# from       : flask-coffee-and-wifi @ 7e66b37733df7fc62e3c81d6d4008211005597df
# source     : main.py:235-250
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def add_bookmark(cafe_id):
    # Check if bookmark is present or not
    existing_bookmark = db.session.execute(
        db.select(Bookmark).filter_by(cafe_id=cafe_id, user_id=current_user.id)).first()

    if existing_bookmark:
        flash("This bookmark already present")
        print("Yes")
        return redirect(url_for('cafes'))

    else:
        new_bookmark = Bookmark(user_id=current_user.id, cafe_id=cafe_id)
        db.session.add(new_bookmark)
        db.session.commit()
        flash("Bookmark done successfully!")
        return redirect(url_for('cafes'))
