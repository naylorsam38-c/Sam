# Harvested by harvest_parts.py
# capability : CAP-0012 (rate item)
# from       : zinny-api @ 65dbe26a4762675fb1ce031a3fc951fb0d784e78
# source     : src/zinny_api/api/ratings.py:96-161
# licence    : BSD-3-Clause (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def save_rating():
    """Save a rating for a title."""
    data = request.get_json()

    title_id = data.get("title_id")
    survey_id = data.get("survey_id")
    ratings = json.dumps(data.get("ratings"))
    comments = data.get("comments", "")
    screen_type_id = data.get("screen_type_id", None)
    screen_type = data.get("screen_type", None)
    conn = get_connection()
    cursor = conn.cursor()

    if not screen_type_id and screen_type:
        # lookup screen_type_id from screen_type
        cursor.execute("SELECT id FROM screen_types WHERE type = ?;", (screen_type,))
        screen_type_id_row_object = cursor.fetchone()
        if not screen_type_id_row_object:
            return jsonify({"error": "Invalid 'screen_type'."}), 400
        screen_type_id = screen_type_id_row_object[0]

    elif screen_type_id and not screen_type:
        # lookup screen_type from screen_type_id
        cursor.execute("SELECT type FROM screen_types WHERE id = ?;", (screen_type_id,))
        screen_type = cursor.fetchone()
        if not screen_type:
            return jsonify({"error": "Invalid 'screen_type_id'."}), 400

    if not title_id or not survey_id or not ratings:
        message = "Missing required fields."
        message += f" title_id: {title_id}, survey_id: {survey_id}, ratings: {ratings}"
        return jsonify({"error": message}), 400

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ratings (title_id, survey_id, screen_type_id, ratings, comments)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(title_id, survey_id) DO UPDATE SET
                screen_type_id = excluded.screen_type_id,
                ratings = excluded.ratings,
                comments = excluded.comments;
            """,
            (title_id, survey_id, screen_type_id, ratings, comments)
        )
        conn.commit()

        # Fetch the ID of the affected record
        cursor.execute(
            """
            SELECT id FROM ratings
            WHERE title_id = ? AND survey_id = ?;
            """,
            (title_id, survey_id)
        )
        rating_id = cursor.fetchone()[0]
             
    except sqlite3.IntegrityError as e:
        return {"error": f"Failed to save rating: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 500
    finally:
        conn.close()

    return jsonify({"message": "Rating saved successfully.", "rating_id": rating_id}), 201
