# Harvested by harvest_parts.py
# capability : CAP-0036 (import data)
# from       : django-folium @ 1f6833904db1375e9326cabd76e19372610bdf60
# source     : django_and_folium/django_and_folium/geo_app/views.py:80-95
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def import_data(request):

    if request.method == 'POST':
        feature_resource = FeatureResource()
        dataset = Dataset()
        new_features = request.FILES.get('importData')

        imported_data = dataset.load(new_features.read().decode('latin1'))
        result = feature_resource.import_data(imported_data, dry_run=True)

        if not result.has_errors():
            # Import now
            feature_resource.import_data(imported_data, dry_run=False)
            messages.success(request, 'Data Imported Successfully.')

    return render(request, 'geoapp/import_data.html')
