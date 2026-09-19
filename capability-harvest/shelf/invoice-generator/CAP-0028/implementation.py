# Harvested by harvest_parts.py
# capability : CAP-0028 (filter list)
# from       : invoice-generator @ 14f0b74b979604e970dc1b14e803581c42e78b2d
# source     : server.py:75-115
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def get_invoices():
    """Fetches a list of invoices with customer names, supporting search, date filtering, and limit."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    search_term = request.args.get('search', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit')

    params = []
    query = """
        SELECT i.id, i.invoice_no, i.date, i.total_value, i.status, c.name as customer_name
        FROM Invoices i JOIN Customers c ON i.customer_id = c.id
    """
    conditions = []
    if search_term:
        conditions.append("(i.invoice_no LIKE ? OR c.name LIKE ? OR i.total_value LIKE ?)")
        params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
    if start_date:
        conditions.append("i.date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("i.date <= ?")
        params.append(end_date)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY i.date DESC, i.id DESC"
    
    if limit:
        query += " LIMIT ?;"
        params.append(int(limit))
    else:
        query += ";"

    cursor.execute(query, params)
    invoices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(invoices)
