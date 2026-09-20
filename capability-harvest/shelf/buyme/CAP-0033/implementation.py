# Harvested by harvest_parts.py
# capability : CAP-0033 (close auction)
# from       : buyme @ 86693e87bde6e8cb34a9cb22893c7c7c1e1caf92
# source     : app/routes/auction.py:682-716
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def end_auction(id):
    """End an auction early (admin/customer rep only)."""
    if not current_user.is_admin and not current_user.is_customer_rep:
        abort(403)
        
    auction = Auction.query.get_or_404(id)
    if not auction.is_active:
        flash('Auction is already ended.', 'warning')
        return redirect(url_for('auction.view', id=id))
        
    auction.is_active = False
    auction.end_time = datetime.utcnow()
    winner = auction.determine_winner()
    
    if winner:
        send_notification_email(
            winner.email,
            'Auction Won',
            f'Congratulations! You have won the auction for "{auction.title}"!'
        )
        send_notification_email(
            auction.seller.email,
            'Auction Ended',
            f'Your auction "{auction.title}" has ended. The winner is {winner.username}.'
        )
    else:
        send_notification_email(
            auction.seller.email,
            'Auction Ended',
            f'Your auction "{auction.title}" has ended. No winner was determined.'
        )
    
    db.session.commit()
    flash('Auction ended successfully.', 'success')
    return redirect(url_for('auction.view', id=id))
