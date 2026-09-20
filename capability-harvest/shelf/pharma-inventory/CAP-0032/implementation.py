# Harvested by harvest_parts.py
# capability : CAP-0032 (scan barcode)
# from       : pharma-inventory @ 42e44bb4690a2aaff432a99631abc490569c1ce0
# source     : app.py:326-345
# licence    : Apache-2.0 (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def get_product_by_barcode(barcode):
    try:
        product = Product.query.filter_by(barcode=barcode).first()
        if product:
            return jsonify({
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'category': product.category,
                    'description': product.description,
                    'unit_price': product.unit_price,
                    'quantity': product.quantity,
                    'reorder_level': product.reorder_level,
                    'barcode': product.barcode,
                    'expiry_date': product.expiry_date.strftime('%Y-%m-%d') if product.expiry_date else None
                }
            })
        return jsonify({'product': None})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
