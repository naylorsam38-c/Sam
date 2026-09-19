# Harvested by harvest_parts.py
# capability : CAP-0016 (register account)
# from       : hospital-management-real @ 2ef9184f817eb880f55685ee2535d49a322e2ca8
# source     : app.py:824-833
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def patient_register():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); phone=request.form.get("phone","").strip()
        if PatientAccount.query.join(Patient).filter(Patient.email==email).first(): flash("An account already exists for this email.","danger"); return redirect(url_for("patient_register"))
        try: age=int(request.form.get("age",0))
        except ValueError: age=0
        patient=Patient(patient_code=generate_patient_code(),name=request.form["name"].strip(),age=age,gender=request.form["gender"],phone=phone,email=email,blood_group=request.form.get("blood_group"))
        db.session.add(patient); db.session.flush(); db.session.add(PatientAccount(patient_id=patient.id,password_hash=generate_password_hash(request.form["password"]))); db.session.commit()
        flash(f"Registration successful. Your patient ID is {patient.patient_code}.","success"); return redirect(url_for("patient_login"))
    return render_template("patient_register.html")
