# Harvested by harvest_parts.py
# capability : CAP-0017 (log in)
# from       : hospital-management-real @ 2ef9184f817eb880f55685ee2535d49a322e2ca8
# source     : app.py:290-304
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, active=True).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["role"] = user.role
            audit("LOGIN", f"User {user.email} logged in")
            db.session.commit()
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")
