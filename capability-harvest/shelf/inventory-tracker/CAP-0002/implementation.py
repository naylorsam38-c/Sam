# Harvested by harvest_parts.py
# capability : CAP-0002 (manage inventory)
# from       : inventory-tracker @ 6aba7fb8ef1b86e1d9e03184476b8bb37fe2bc12
# source     : app.py:49-62
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def update_stock(id):
    # Determine if we are adding or removing stock
    action = request.form['action']
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if action == 'sell':
        c.execute("UPDATE products SET quantity = quantity - 1 WHERE id = ?", (id,))
    elif action == 'restock':
        c.execute("UPDATE products SET quantity = quantity + 1 WHERE id = ?", (id,))
        
    conn.commit()
    conn.close()
    return redirect(url_for('index'))
