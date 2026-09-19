# Harvested by harvest_parts.py
# capability : CAP-0023 (edit profile)
# from       : dataviva-training @ 284d831a2c1b0b6109ac3c964aa0190225f8a25f
# source     : app/routes.py:103-115
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Suas mudanças foram salvas.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile/edit_profile.html', title='Editar Perfil',
                           form=form)
