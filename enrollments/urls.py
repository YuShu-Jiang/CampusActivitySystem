from django.urls import path
from . import views

urlpatterns = [
    path('', views.EnrollmentListView.as_view(), name='enrollment-list'),
    path('<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment-detail'),
    path('export/<int:activity_id>/', views.ExportEnrollmentsView.as_view(), name='export-enrollments'),
]