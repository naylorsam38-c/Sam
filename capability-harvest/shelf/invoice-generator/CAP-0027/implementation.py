# Harvested by harvest_parts.py
# capability : CAP-0027 (view record detail)
# from       : invoice-generator @ 14f0b74b979604e970dc1b14e803581c42e78b2d
# source     : server.py:539-570
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def get_invoice_details(invoice_id):
    """Fetches full details for a single invoice for editing."""
    try:
        conn = get_db_connection()
        # Fetch main invoice details
        invoice = conn.execute('SELECT * FROM Invoices WHERE id = ?', (invoice_id,)).fetchone()
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404

        # Fetch customer details
        customer = conn.execute('SELECT * FROM Customers WHERE id = ?', (invoice['customer_id'],)).fetchone()
        
        # Fetch invoice items
        items = conn.execute("""
            SELECT ii.*, i.name as item_name, i.default_mrp
            FROM Invoice_Items ii
            JOIN Items i ON ii.item_id = i.id
            WHERE ii.invoice_id = ?
        """, (invoice_id,)).fetchall()

        conn.close()

        # Prepare the response
        response_data = {
            'invoice': dict(invoice),
            'customer': dict(customer),
            'items': [dict(item) for item in items]
        }
        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
