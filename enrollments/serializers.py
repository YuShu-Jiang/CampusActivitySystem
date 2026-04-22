from rest_framework import serializers
from .models import Enrollment
from activities.models import Activity  # 新增导入
from django.contrib.auth.models import User


# 创建一个简化的活动序列化器，避免循环导入
class ActivitySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ['id', 'title', 'start_time', 'location', 'status']


class EnrollmentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # 添加只读的user_id字段
    activity = ActivitySimpleSerializer(read_only=True)  # 使用简化版
    activity_id = serializers.PrimaryKeyRelatedField(
        queryset=Activity.objects.all(),  # 现在 Activity 已导入
        source='activity',
        write_only=True
    )

    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'user_id', 'activity', 'activity_id',
            'enrollment_time', 'status', 'notes'
        ]
        read_only_fields = ['enrollment_time']