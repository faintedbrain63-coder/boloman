from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Boloman backup admin"
admin.site.site_title = "Boloman"
admin.site.index_title = "Catalog, orders, and inventory"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("account/", include("accounts.urls")),
    path("products/", include("store.urls")),
    path("orders/", include("orders.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
