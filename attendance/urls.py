from django.urls import path
from . import views

urlpatterns = [
    path('', views.AttendanceRootView.as_view(), name='attendance-root'),
    path('generate-qrcode/', views.QRCodeGenerateView.as_view(), name='generate-qrcode'),
    path('checkin/', views.QRCodeCheckinView.as_view(), name='checkin'),
    path('manual-checkin/', views.ManualCheckinView.as_view(), name='manual-checkin'),
    path('records/', views.AttendanceListView.as_view(), name='attendance-list'),
    path('records/<int:pk>/', views.AttendanceDetailView.as_view(), name='attendance-detail'),
    path('activity-attendance/', views.ActivityAttendanceView.as_view(), name='activity-attendance'),
]