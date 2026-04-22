from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """自定义JWT登录序列化器，支持学号登录"""
    
    def validate(self, attrs):
        # 尝试使用用户名登录
        try:
            return super().validate(attrs)
        except Exception:
            # 用户名登录失败，尝试使用学号登录
            username = attrs.get('username')
            password = attrs.get('password')
            
            if not username or not password:
                raise serializers.ValidationError("用户名和密码不能为空")
            
            # 通过学号查找用户
            try:
                profile = UserProfile.objects.get(student_id=username)
                user = profile.user
                
                # 验证密码
                if not user.check_password(password):
                    raise serializers.ValidationError("密码错误")
                
                # 生成令牌
                refresh = self.get_token(user)
                return {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            except UserProfile.DoesNotExist:
                raise serializers.ValidationError("用户不存在")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['student_id', 'phone', 'role', 'college', 'major', 'avatar']
        read_only_fields = ['role']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    student_id = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    college = serializers.CharField(write_only=True, required=False, allow_blank=True)
    major = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2',
                  'student_id', 'phone', 'college', 'major']

    def validate(self, data):
        # 验证两次密码是否一致
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "两次密码不一致"})

        # 验证用户名是否已存在
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "该用户名已被使用"})

        # 验证学号是否已存在
        if UserProfile.objects.filter(student_id=data['student_id']).exists():
            raise serializers.ValidationError({"student_id": "该学号已被注册"})

        return data

    def create(self, validated_data):
        # 移除不需要的字段
        password2 = validated_data.pop('password2')
        student_id = validated_data.pop('student_id')
        phone = validated_data.pop('phone', '')
        college = validated_data.pop('college', '')
        major = validated_data.pop('major', '')

        # 创建用户
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )

        # 更新用户扩展信息（由post_save信号自动创建）
        if hasattr(user, 'profile'):
            profile = user.profile
            profile.student_id = student_id
            profile.phone = phone or None
            profile.college = college or None
            profile.major = major or None
            profile.save()

        return user