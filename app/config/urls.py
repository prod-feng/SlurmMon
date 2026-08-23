from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    #path("", include("apps.cluster.urls")),
    path("nodes/", include("apps.nodes.urls")),
    path("partitions/", include("apps.partitions.urls")),
    path("jobs/", include("apps.jobs.urls")),
    path("accounts/",include("apps.accounts.urls")),

]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )

