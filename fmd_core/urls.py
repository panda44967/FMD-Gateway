from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FmdCsvUploadView,
    SupplierPartViewSet,
    ReviewTaskViewSet,
    RegulatoryRuleViewSet,
    ReevaluateView,
    RegulatoryStatusView,
    RegulatorySyncView,
    OverviewStatsView,
    FmdDynamicTemplateDownloadView,
    SupplierPortalContextView,
    SupplierDemoResetView,
    AiDocumentExtractView,
    AiDocumentCommitView,
    SampleDownloadView
)

router = DefaultRouter()
router.register(r'parts', SupplierPartViewSet, basename='parts')
router.register(r'tasks', ReviewTaskViewSet, basename='tasks')
router.register(r'rules', RegulatoryRuleViewSet, basename='rules')

urlpatterns = [
    path('supplier/context/', SupplierPortalContextView.as_view(), name='supplier-portal-context'),
    path('supplier/reset-demo/', SupplierDemoResetView.as_view(), name='supplier-demo-reset'),
    path('fmd/upload/', FmdCsvUploadView.as_view(), name='fmd-upload'),
    path('fmd/template/download/', FmdDynamicTemplateDownloadView.as_view(), name='fmd-template-download'),
    path('fmd/samples/download/', SampleDownloadView.as_view(), name='sample-download'),
    path('fmd/ai-extract/', AiDocumentExtractView.as_view(), name='fmd-ai-extract'),
    path('fmd/ai-commit/', AiDocumentCommitView.as_view(), name='fmd-ai-commit'),
    path('regulations/reevaluate/', ReevaluateView.as_view(), name='fmd-reevaluate'),
    path('regulations/status/', RegulatoryStatusView.as_view(), name='regulations-status'),
    path('regulations/sync/', RegulatorySyncView.as_view(), name='regulations-sync'),
    path('overview/stats/', OverviewStatsView.as_view(), name='overview-stats'),
    path('', include(router.urls)),
]
