from django.contrib import admin
from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'checkin_time', 'checkin_method')
    list_filter = ('checkin_method', 'checkin_time')
    search_fields = ('enrollment__user__username', 'enrollment__activity__title')