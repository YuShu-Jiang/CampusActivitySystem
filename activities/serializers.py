from rest_framework import serializers
from .models import Activity
from django.contrib.auth.models import User


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class ActivitySerializer(serializers.ModelSerializer):
    organizer = UserSimpleSerializer(read_only=True)
    organizer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='organizer',
        write_only=True,
        required=False
    )

    # 计算字段
    is_registration_open = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'organizer', 'organizer_id',
            'location', 'start_time', 'end_time', 'registration_deadline',
            'max_participants', 'current_participants', 'cover_image',
            'status', 'is_registration_open', 'available_slots', 'category',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['current_participants', 'created_at', 'updated_at']

    def get_is_registration_open(self, obj):
        from django.utils import timezone
        now = timezone.now()
        return now <= obj.registration_deadline and obj.status == 'published'

    def get_available_slots(self, obj):
        if obj.max_participants == 0:
            return "不限"
        available = obj.max_participants - obj.current_participants
        return max(available, 0)
    
    def update(self, instance, validated_data):
        # 调用父类的update方法
        instance = super().update(instance, validated_data)
        
        # 根据时间自动更新活动状态
        from django.utils import timezone
        now = timezone.now()
        
        # 只有在状态不是cancelled的情况下才自动更新
        if instance.status != 'cancelled':
            if now < instance.start_time:
                # 活动开始前：已发布
                instance.status = 'published'
            elif now >= instance.start_time and now <= instance.end_time:
                # 活动进行中：进行中
                instance.status = 'ongoing'
            elif now > instance.end_time:
                # 活动结束后：已结束
                instance.status = 'completed'
            instance.save()
        
        return instance
    
    def to_representation(self, instance):
        # 获取原始序列化数据
        data = super().to_representation(instance)
        
        # 如果没有封面图片，设置默认图片
        if not data.get('cover_image'):
            data['cover_image'] = '/static/images/default-activity.jpg'
            
        return data

    def validate(self, data):
        # 如果只更新status字段为'cancelled'，不需要验证其他字段
        if len(data) == 1 and 'status' in data and data['status'] == 'cancelled':
            return data

        # 验证必要字段是否存在
        required_fields = ['end_time', 'start_time', 'registration_deadline']
        for field in required_fields:
            if field not in data:
                raise serializers.ValidationError(f"{field}字段是必填项")

        # 验证时间逻辑
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError("结束时间必须晚于开始时间")

        if data['registration_deadline'] > data['start_time']:
            raise serializers.ValidationError("报名截止时间不能晚于活动开始时间")

        # 处理max_participants字段
        if 'max_participants' in data:
            if data['max_participants'] is None:
                data['max_participants'] = 0
            elif data['max_participants'] < 0:
                raise serializers.ValidationError("最大参与人数不能为负数")
        # 如果max_participants字段不存在，设置默认值0
        else:
            data['max_participants'] = 0

        return data