# Harvested by harvest_parts.py
# capability : CAP-0007 (generate report)
# from       : fintrack @ 948a9a007776488607e55971687970bc25874ddc
# source     : app/routes/reports.py:33-56
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def generate_report():
    user_id = session["user_id"]
    user = db.execute("SELECT username FROM users WHERE id = ?", user_id)[0]
    expenses = _user_expenses(user_id)

    if request.method == "POST":
        report_type = request.form.get("report_type")
        report_currency = request.form.get("report_currency", "USD")

        rates = get_exchange_rates("USD")
        rate = rates.get(report_currency, 1)

        converted_expenses = []
        for expense in expenses:
            converted_expenses.append({
                **expense, "converted_amount": round(expense["amount"] * rate, 2)
            })

        if report_type == "pdf":
            return _build_pdf_report(user["username"], report_currency, converted_expenses)
        if report_type == "excel":
            return _build_excel_report(converted_expenses)

    return render_template("generate_report.html", has_expenses=bool(expenses))
