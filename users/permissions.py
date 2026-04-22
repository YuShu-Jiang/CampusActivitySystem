from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """只允许管理员访问"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'profile') and request.user.profile.role == 'admin'


class IsOrganizerOrAdmin(permissions.BasePermission):
    """允许活动组织者或管理员访问"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        return profile.role in ['organizer', 'admin']


class IsStudent(permissions.BasePermission):
    """只允许学生访问"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        return profile.role == 'student'


class IsActivityOwnerOrAdmin(permissions.BasePermission):
    """只允许活动创建者或管理员访问"""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False

        # 管理员可以访问所有
        if profile.role == 'admin':
            return True

        # 检查是否是活动创建者
        return hasattr(obj, 'created_by') and obj.created_by == request.user