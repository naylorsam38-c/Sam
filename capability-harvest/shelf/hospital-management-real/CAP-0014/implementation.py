# Harvested by harvest_parts.py
# capability : CAP-0014 (book slot)
# from       : hospital-management-real @ 2ef9184f817eb880f55685ee2535d49a322e2ca8
# source     : app.py:864-878
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def patient_book():
    patient=Patient.query.get_or_404(session["patient_id"]); doctor_id=int(request.form["doctor_id"]); dt=datetime.fromisoformat(request.form["appointment_date"])
    doctor=Doctor.query.get_or_404(doctor_id)
    now_local = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
    if not doctor.available: flash("Doctor is unavailable.","danger"); return redirect(url_for("patient_portal"))
    if dt < now_local: flash("Please select a future date and time.","danger"); return redirect(url_for("patient_portal"))
    if dt.minute not in (0,30) or dt.hour<9 or dt.hour>=17: flash("Please select a valid 30-minute slot between 9 AM and 5 PM.","danger"); return redirect(url_for("patient_portal"))
    conflict=Appointment.query.filter_by(doctor_id=doctor_id,appointment_date=dt,status="Scheduled").first()
    if conflict: flash("Sorry, that slot was just booked. Please choose another.","danger"); return redirect(url_for("patient_portal"))
    ap=Appointment(patient_id=patient.id,doctor_id=doctor_id,appointment_date=dt,reason=request.form.get("reason")); db.session.add(ap); db.session.commit()
    try:
        sent=send_confirmation_email(patient.email,patient.name,doctor.name,dt)
        flash("Appointment booked and confirmation email sent." if sent else "Appointment booked successfully. Configure SMTP in .env for email confirmation.","success")
    except Exception: flash("Appointment booked. Email could not be sent; your booking is still saved.","warning")
    return redirect(url_for("patient_portal"))
