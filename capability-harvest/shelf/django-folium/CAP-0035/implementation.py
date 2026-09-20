# Harvested by harvest_parts.py
# capability : CAP-0035 (show map)
# from       : django-folium @ 1f6833904db1375e9326cabd76e19372610bdf60
# source     : django_and_folium/django_and_folium/geo_app/views.py:20-22
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def index(request):
    map = basemap(request)
    return render(request, 'geoapp/map.html', map)
