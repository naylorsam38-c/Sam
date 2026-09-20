# Harvested by harvest_parts.py
# capability : CAP-0003 (search records)
# from       : hostelfix @ 8d54ca9aebe956eb135f53fdb8aabb4e3a5a8748
# source     : app.py:213-229
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def search():
    query = request.args.get('query')
    search_results = Hostel.query.filter(Hostel.name.ilike(f'%{query}%')).all()

    # Prepare list of hostels with images
    hostels_with_images = []
    for hostel in search_results:
        hostel_images_dir = os.path.join('static', 'images', hostel.name)
        if os.path.exists(hostel_images_dir):
            images = os.listdir(hostel_images_dir)
            images = [img for img in images if img.endswith(('png', 'jpg', 'jpeg', 'gif'))]
        else:
            images = []  # No images found

        hostels_with_images.append({'hostel': hostel, 'images': images})

    return render_template('search_results.html', query=query, hostels_with_images=hostels_with_images)
