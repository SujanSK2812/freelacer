import os

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'freelancer_portal.settings'
)

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()


from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import messages_app.routing


application = ProtocolTypeRouter({

    "http": django_asgi_app,

    "websocket": AuthMiddlewareStack(

        URLRouter(
            messages_app.routing.websocket_urlpatterns
        )

    ),

})