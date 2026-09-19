# Harvested by harvest_parts.py
# capability : CAP-0001 (export data)
# from       : monthly-expenses-tracker @ 7fd04edb0756e8dda501ee01b98dc30de2d238b6
# source     : app/routes.py:358-381
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def export_csv():
    data    = load_data(current_user.id)
    total   = sum(e['amount'] for e in data['expenses'])
    balance = calculate_balance(data['salary'], data['expenses'])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Description', 'Category', 'Amount'])
    for e in data['expenses']:
        writer.writerow([e['expense_date'], e['description'], e.get('category', 'Uncategorized'),
                         f"{e['amount']:.2f}"])
    writer.writerow([])
    writer.writerow(['--- SUMMARY ---', '', ''])
    writer.writerow(['Monthly Salary',    '', f"{data['salary']:.2f}"])
    writer.writerow(['Total Expenses',    '', f"{total:.2f}"])
    writer.writerow(['Remaining Balance', '', f"{balance:.2f}"])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='budget_export.csv'
    )
