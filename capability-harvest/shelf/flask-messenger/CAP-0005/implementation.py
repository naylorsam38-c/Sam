# Harvested by harvest_parts.py
# capability : CAP-0005 (send message)
# from       : flask-messenger @ 4e9a9b31b5fc091a38f3162fb9cb9b579c11a047
# source     : messenger.py:30-36
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def _add_message(message, sender):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()
        q = "INSERT INTO messages VALUES (NULL, datetime('now'),?,?)"
        c.execute(q, (message, sender))
        conn.commit()
        return c.lastrowid
