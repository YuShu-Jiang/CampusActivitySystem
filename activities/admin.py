from django.contrib import admin
from .models import Activity

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'location', 'start_time', 'status', 'current_participants', 'max_participants')
    list_filter = ('status', 'organizer')
    search_fields = ('title', 'description', 'location')
    date_hierarchy = 'start_time'