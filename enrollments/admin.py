from django.contrib import admin
from .models import Enrollment

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'enrollment_time', 'status')
    list_filter = ('status', 'activity')
    search_fields = ('user__username', 'activity__title')