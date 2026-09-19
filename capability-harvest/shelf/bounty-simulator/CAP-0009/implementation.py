# Harvested by harvest_parts.py
# capability : CAP-0009 (show leaderboard)
# from       : bounty-simulator @ 53bd597ccd9d9469e6bd15618817584ec404eb06
# source     : backend/main.py:86-88
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def leaderboard():
    users = User.query.order_by(User.xp.desc()).limit(50).all()
    return jsonify([{"id": u.id, "username": u.username, "xp": u.xp, "rank": u.rank} for u in users])
