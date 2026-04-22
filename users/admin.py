from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


# 内联显示用户扩展信息
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = '扩展信息'


# 自定义用户管理界面
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')
    search_fields = ('username', 'email', 'profile__student_id')

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '未设置'

    get_role.short_description = '角色'


# 重新注册用户管理界面
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# 注册UserProfile
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'role', 'college', 'major')
    list_filter = ('role', 'college')
    search_fields = ('user__username', 'student_id', 'college')