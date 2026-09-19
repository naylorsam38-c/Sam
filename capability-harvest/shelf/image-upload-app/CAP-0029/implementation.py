# Harvested by harvest_parts.py
# capability : CAP-0029 (capture photo)
# from       : image-upload-app @ 227f005343bd815e2f5360ab818beb6b93cf9b48
# source     : app.py:62-81
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def capture():
    filename=''     # using filename variable to display video feed and captured image alternatively on the same page
    image_data_url = request.form.get('image')
    if request.method == 'POST':
        # Decode the base64 data URL to obtain the image data
        image_data = base64.b64decode(image_data_url.split(',')[1])
        # Create an image from the decoded data
        img = Image.open(BytesIO(image_data))
        # Generate a filename with the current date and time
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        filename = f"img_{timestamp}.png"  # Change file extension to 'png'
        print(filename)
        # Save the image in PNG format
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(file_path, 'PNG')
        error_message = 'Image successfully captured'
        # use if you want to display all the images in the folder
        # image_files = os.listdir(app.config['UPLOAD_FOLDER'])
        return render_template('capture.html', filename=filename)
    return render_template('capture.html', filename=filename)
