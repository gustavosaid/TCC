
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from registro.api.views import FuncionarioViewSet, TreinamentoViewSet, ColetaFacesViewSet

router = DefaultRouter()
router.register('funcionarios', FuncionarioViewSet)
router.register('treinamento', TreinamentoViewSet)
router.register('coletaFace', ColetaFacesViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',include(router.urls)),
    path('', include('registro.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
