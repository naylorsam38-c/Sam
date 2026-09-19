# Harvested by harvest_parts.py
# capability : CAP-0025 (edit record)
# from       : invoice-generator @ 14f0b74b979604e970dc1b14e803581c42e78b2d
# source     : server.py:573-625
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def update_invoice(invoice_id):
    """Updates an existing invoice."""
    data = request.get_json()
    if not data or not data.get('customer_id') or not data.get('items'):
        return jsonify({'error': 'Missing required invoice data'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Start a transaction
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Delete old invoice items
        cursor.execute("DELETE FROM Invoice_Items WHERE invoice_id = ?", (invoice_id,))

        # 2. Update the main invoice table
        cursor.execute("""
            UPDATE Invoices 
            SET invoice_no = ?, date = ?, customer_id = ?, sale_type = ?, notes = ?, 
                total_value = ?, taxable_value = ?, cgst = ?, sgst = ?, igst = ?, 
                cess = ?, round_off = ?, status = ?
            WHERE id = ?
        """, (
            data['invoice_no'], data['date'], data['customer_id'], data.get('sale_type', 'CASH'),
            data.get('notes'), data['total_value'], data['taxable_value'], data['cgst'],
            data['sgst'], data.get('igst', 0), data.get('cess', 0), data['round_off'], 'PAID',
            invoice_id
        ))

        # 3. Insert the new/updated invoice items
        items_to_insert = []
        for item in data['items']:
            items_to_insert.append((
                invoice_id, item['item_id'], item.get('quantity', 1), item.get('free_quantity', 0),
                item.get('unit', 'PCS'), item['price_per_unit'], item.get('discount', 0),
                item['gst_rate'], item['cgst_amount'], item['sgst_amount'], item.get('igst_amount', 0),
                item.get('cess_amount', 0), item['total_amount'], item.get('hsn_code')
            ))

        cursor.executemany("""
            INSERT INTO Invoice_Items (invoice_id, item_id, quantity, free_quantity, unit, 
                                       price_per_unit, discount, gst_rate, cgst_amount, 
                                       sgst_amount, igst_amount, cess_amount, total_amount, hsn_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, items_to_insert)

        conn.commit()
        return jsonify({'message': 'Invoice updated successfully', 'invoice_id': invoice_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
