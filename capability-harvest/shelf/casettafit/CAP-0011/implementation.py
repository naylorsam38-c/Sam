# Harvested by harvest_parts.py
# capability : CAP-0011 (log workout)
# from       : casettafit @ 5c5737130c8052d7c7094ae5c45df29bcb93b635
# source     : app/routes/workout.py:211-272
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def log_set(session_id):
    """Log a set during workout"""
    session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
        is_completed=False  # Prevent logging to completed sessions
    ).first_or_404()
    
    data = request.json
    exercise_id = data.get('exercise_id')
    set_number = data.get('set_number')
    reps = data.get('reps')
    weight = data.get('weight')
    rpe = data.get('rpe')
    notes = data.get('notes', '')
    
    if not exercise_id or not set_number:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    # Validate set_number is positive
    if set_number < 1:
        return jsonify({'success': False, 'error': 'Invalid set number'}), 400
    
    # Check if this set already exists (update case)
    existing_set = WorkoutSet.query.filter_by(
        workout_session_id=session_id,
        exercise_id=exercise_id,
        set_number=set_number
    ).first()
    
    if existing_set:
        # Update existing set
        existing_set.reps = reps
        existing_set.weight = weight
        existing_set.rpe = rpe
        existing_set.notes = notes
        existing_set.completed_at = datetime.utcnow()
        workout_set = existing_set
    else:
        # Create new set
        workout_set = WorkoutSet(
            workout_session_id=session_id,
            exercise_id=exercise_id,
            set_number=set_number,
            reps=reps,
            weight=weight,
            rpe=rpe,
            notes=notes,
            completed_at=datetime.utcnow()
        )
        db.session.add(workout_set)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'set_id': workout_set.id,
        'set_number': workout_set.set_number,
        'reps': workout_set.reps,
        'weight': workout_set.weight,
        'rpe': workout_set.rpe
    })
