from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('fmd_core.urls')),
    path('supplier/', TemplateView.as_view(template_name='supplier.html'), name='supplier-portal'),
    path('', TemplateView.as_view(template_name='index.html')),
    # Serve root static assets directly for index.html (styles.css, engine.js, xlsx, etc.)
    re_path(r'^(?P<path>.*\.(css|js|csv|ico|png|jpg|svg|xlsx|xls))$', serve, {'document_root': settings.BASE_DIR}),
]
