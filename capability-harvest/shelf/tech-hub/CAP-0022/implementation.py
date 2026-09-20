# Harvested by harvest_parts.py
# capability : CAP-0022 (verify email)
# from       : tech-hub @ 8d1f31982401ab0d08ff34e6f4207e10310313fd
# source     : app/routes.py:65-83
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def verify_email(token):
    if current_user.is_authenticated and current_user.email_verified:
        return redirect(url_for('main.index'))
    
    email = verify_email_token(token)
    if not email:
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(email=email).first_or_404()
    if user.email_verified:
        flash('Account already verified.', 'info')
    else:
        user.email_verified = True
        user.verification_token = None
        db.session.commit()
        flash('Thank you for verifying your email address!', 'success')
    
    return redirect(url_for('main.index'))
