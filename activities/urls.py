from django.urls import path
from . import views

urlpatterns = [
    path('', views.ActivityListView.as_view(), name='activity-list'),
    path('upcoming/', views.UpcomingActivitiesView.as_view(), name='upcoming-activities'),
    path('my/', views.MyActivitiesView.as_view(), name='my-activities'),
    path('stats/', views.OrganizerStatsView.as_view(), name='organizer-stats'),
    path('analytics/', views.ActivityAnalyticsView.as_view(), name='activity-analytics'),
    path('platform-stats/', views.PlatformStatsView.as_view(), name='platform-stats'),
    path('<int:pk>/', views.ActivityDetailView.as_view(), name='activity-detail'),
]