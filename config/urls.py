from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from config.views import home_view, api_root_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('api/', api_root_view, name='api_root'),
    path('api/auth/', include('users.urls')),
    path('api/activities/', include('activities.urls')),
    path('api/enrollments/', include('enrollments.urls')),
    path('api/attendance/', include('attendance.urls')),

    # 页面路由 - 添加缺失的路由
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),
    path('register/', TemplateView.as_view(template_name='register.html'), name='register'),
    path('activities/', TemplateView.as_view(template_name='activities.html'), name='activities_list'),
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
    path('checkin/', TemplateView.as_view(template_name='checkin.html'), name='checkin'),

    # 新增路由 - 解决404问题
    path('my-activities/', TemplateView.as_view(template_name='my_activities.html'), name='my_activities'),
    path('attendance-management/', TemplateView.as_view(template_name='attendance_management.html'),
         name='attendance_management'),
    path('organizer-dashboard/', TemplateView.as_view(template_name='organizer_dashboard.html'),
         name='organizer_dashboard'),
    path('student-dashboard/', TemplateView.as_view(template_name='student_dashboard.html'), name='student_dashboard'),
    path('my-enrollments/', TemplateView.as_view(template_name='my_enrollments.html'), name='my_enrollments'),
    path('admin-dashboard/', TemplateView.as_view(template_name='admin_dashboard.html'), name='admin_dashboard'),
    path('admin/users/', TemplateView.as_view(template_name='admin_users.html'), name='admin_users'),
    path('admin/statistics/', TemplateView.as_view(template_name='admin_statistics.html'), name='admin_statistics'),
    path('system-settings/', TemplateView.as_view(template_name='system_settings.html'), name='system_settings'),
    path('activity-analytics/', TemplateView.as_view(template_name='activity_analytics.html'), name='activity_analytics'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)