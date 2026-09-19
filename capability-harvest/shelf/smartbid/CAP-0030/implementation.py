# Harvested by harvest_parts.py
# capability : CAP-0030 (place bid)
# from       : smartbid @ ccc3e0de84a20dedd6ab2cc866a12cb5125f2279
# source     : app/routes/auctions.py:128-201
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def place_bid(auction_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    amount = data.get('amount')
    if amount is None:
        return jsonify({'error': 'amount is required'}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'amount must be a positive number'}), 400

    try:
        with db.session.begin():
            result = db.session.execute(
                select(Auction).where(Auction.id == auction_id).with_for_update()
            )
            auction = result.scalar_one_or_none()

            if auction is None:
                raise ValueError('Auction not found')

            if auction.status != 'active':
                raise PermissionError(f'Auction is {auction.status}')

            if auction.is_expired():
                auction.status = 'ended'
                winning_bid = (
                    Bid.query
                    .filter_by(auction_id=auction.id)
                    .order_by(Bid.id.desc())
                    .first()
                )
                if winning_bid:
                    auction.winner_id = winning_bid.bidder_id
                raise PermissionError('Auction has expired')

            if auction.seller_id == g.current_user_id:
                raise PermissionError('Seller cannot bid on their own auction')

            min_required = auction.current_price + auction.min_increment
            if amount <= auction.current_price or amount < min_required:
                raise ValueError(
                    f'Bid must be greater than current price ({auction.current_price}) '
                    f'by at least {auction.min_increment}. Minimum bid: {min_required}'
                )

            encrypted_amount = encrypt_bid_amount(amount)

            bid = Bid(
                auction_id=auction_id,
                bidder_id=g.current_user_id,
                encrypted_amount=encrypted_amount
            )
            db.session.add(bid)
            auction.current_price = amount

    except ValueError as e:
        msg = str(e)
        if 'not found' in msg.lower():
            return jsonify({'error': msg}), 404
        return jsonify({'error': msg}), 400
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403

    return jsonify({
        'message': 'Bid placed successfully',
        'bid': bid.to_dict(),
        'new_current_price': auction.current_price
    }), 201
