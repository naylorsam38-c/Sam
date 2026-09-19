# Harvested by harvest_parts.py
# capability : CAP-0008 (award badge)
# from       : bounty-simulator @ 53bd597ccd9d9469e6bd15618817584ec404eb06
# source     : backend/main.py:36-40
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def check_badges(user):
    for xp, badge in BADGE_MILESTONES:
        if user.xp >= xp and not Badge.query.filter_by(user_id=user.id, badge_name=badge).first():
            db.session.add(Badge(user_id=user.id, badge_name=badge))
    db.session.commit()
