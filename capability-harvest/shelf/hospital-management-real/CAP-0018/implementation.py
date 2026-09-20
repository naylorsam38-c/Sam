# Harvested by harvest_parts.py
# capability : CAP-0018 (log out)
# from       : hospital-management-real @ 2ef9184f817eb880f55685ee2535d49a322e2ca8
# source     : app.py:308-313
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def logout():
    if session.get("user_id"):
        audit("LOGOUT", "User logged out")
        db.session.commit()
    session.clear()
    return redirect(url_for("login"))
