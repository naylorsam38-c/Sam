# Harvested by harvest_parts.py
# capability : CAP-0021 (set permissions)
# from       : enterprise-project @ b2965b6b8af0cd0a32f47b02ee266fa0b7b7b54e
# source     : app/admin/routes.py:106-152
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def update_role(entry_id: int):
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400

    new_role = data.get('role')     

    if new_role not in ['staff', 'manager', 'admin']:
        return jsonify({
            'success': False,
            'message': f'Invalid role: {new_role}'
        }), 400
    
    whitelist_entry = Whitelist.query.get_or_404(entry_id)
    user = whitelist_entry.get_user()

    if not user:
        return jsonify({
            'success': False,
            'message': 'No linked user'
        }), 404

    if user.id == current_user.id and new_role != 'admin':
        return jsonify({
            'success': False,
            'message': 'Cannot change your own role'
        }), 403

    try:
        user.role = UserRole.from_string(new_role)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f'Unexpected role update error: {exc}')
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred while updating the user role.'
        }), 500

    return jsonify({
        'success': True,
        'message': f"{user.username}'s role was updated to {new_role}."
    })
