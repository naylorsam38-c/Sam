# Harvested by harvest_parts.py
# capability : CAP-0034 (apply discount code)
# from       : mini-amazon @ ce13c893cafbf79119703d2c662d094e1cd9e01f
# source     : app/cart.py:113-124
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def apply_coupon():
    coupon_id = request.form.get('coupon_code')

    print(coupon_id)

    if not coupon_id:
        return redirect(url_for('cart.cart'))

    message = Coupon.apply_coupon(current_user.id, coupon_id)
    flash(message, 'success' if 'successfully' in message else 'danger')

    return redirect(url_for('cart.cart'))
