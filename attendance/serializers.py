from rest_framework import serializers
from .models import Attendance
from enrollments.models import Enrollment


# 创建一个简化的报名序列化器，避免循环导入
class EnrollmentSimpleSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    activity = serializers.StringRelatedField()

    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'activity']


class AttendanceSerializer(serializers.ModelSerializer):
    enrollment = EnrollmentSimpleSerializer(read_only=True)
    enrollment_id = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment.objects.all(),
        source='enrollment',
        write_only=True
    )
    # 添加一个只读的enrollment_id字段，用于前端显示
    enrollment_id_readonly = serializers.IntegerField(source='enrollment.id', read_only=True)
    
    # 前端需要的额外字段
    activity_id = serializers.IntegerField(source='enrollment.activity.id', read_only=True)
    activity_title = serializers.CharField(source='enrollment.activity.title', read_only=True)
    student_id = serializers.SerializerMethodField(read_only=True)
    student_name = serializers.CharField(source='enrollment.user.username', read_only=True)
    user_id = serializers.IntegerField(source='enrollment.user.id', read_only=True)
    status = serializers.SerializerMethodField(read_only=True)

    def get_student_id(self, obj):
        if hasattr(obj.enrollment.user, 'profile'):
            return obj.enrollment.user.profile.student_id
        return None
    
    def get_status(self, obj):
        if obj.checkin_time:
            return 'checked_in'
        return 'not_checked_in'

    class Meta:
        model = Attendance
        fields = [
            'id', 'enrollment', 'enrollment_id', 'enrollment_id_readonly',
            'checkin_time', 'checkin_method',
            'device_info', 'ip_address', 'qr_token',
            'activity_id', 'activity_title',
            'student_id', 'student_name', 'user_id',
            'status'
        ]
        read_only_fields = ['checkin_time']