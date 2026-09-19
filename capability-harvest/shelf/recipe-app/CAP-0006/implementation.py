# Harvested by harvest_parts.py
# capability : CAP-0006 (write review)
# from       : recipe-app @ da7fdc8337d191228b1b1ffedffaabdb3291c7dc
# source     : routes/comments.py:18-36
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def make_comment(recipe_id):
    comment_text = request.form['comment_text'].strip()

    if not comment_text:
        flash('No comment text', 'error')
        return redirect(url_for('recipes.recipe', recipe_id=recipe_id))
    connection = db_connection()

    try:
        connection.execute('''INSERT INTO comment (user_id, recipe_id, comment_text)
                            VALUES (?, ?, ?)''', (session['user_id'], recipe_id, comment_text))
        connection.commit()
        flash('Comment successfully added', 'success')
    except Exception as e:
        flash(f'Error making comment: {str(e)}', 'error')
    finally:
        connection.close()
    
    return redirect(url_for('recipes.recipe', recipe_id=recipe_id))
