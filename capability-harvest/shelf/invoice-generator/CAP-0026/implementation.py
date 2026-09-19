# Harvested by harvest_parts.py
# capability : CAP-0026 (delete record)
# from       : invoice-generator @ 14f0b74b979604e970dc1b14e803581c42e78b2d
# source     : server.py:60-72
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def delete_invoice(invoice_id):
    """Deletes an invoice and its associated items from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Invoices WHERE id = ?", (invoice_id,))
        conn.commit()
        conn.close()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Invoice not found'}), 404
        return jsonify({'message': 'Invoice deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
