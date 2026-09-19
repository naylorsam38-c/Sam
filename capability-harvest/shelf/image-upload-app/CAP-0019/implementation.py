# Harvested by harvest_parts.py
# capability : CAP-0019 (upload image)
# from       : image-upload-app @ 227f005343bd815e2f5360ab818beb6b93cf9b48
# source     : app.py:86-112
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def upload_image():
    error_message = None
    if 'image' not in request.files:
        error_message = 'image input is required in the form'
        print(error_message)
    else:
        file = request.files['image']
        # if user does not select file, browser also submit an empty part without filename
        if file.filename == '':
            error_message = 'image not selected'
            print(error_message)
        # check if the file is allowed or not by checking its extension
        elif not allowed_images(file.filename):
            error_message = 'invalid image format, allowed formats are - png, jpg, jpeg, gif only'
            print(error_message)
        else:
            # secure_filename is used to sanitize and secure filename before storing it
            filename = secure_filename(file.filename)
            # check if the file with the same name already exists or not
            if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                error_message = 'Image with the same name already exists.'
                print(error_message)
            else:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                print('Image successfully uploaded')
                return redirect(url_for('image', filename=filename))
        return render_template('upload.html', error_message=error_message)
