import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "norsu_bsc_website.settings")

application = get_wsgi_application()

