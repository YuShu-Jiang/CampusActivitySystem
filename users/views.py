from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import UserProfile
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer
)


@method_decorator(csrf_exempt, name='dispatch')
class UserRegistrationView(APIView):
    """用户注册视图"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # 生成JWT令牌
            refresh = RefreshToken.for_user(user)

            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': '注册成功'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class UserLoginView(TokenObtainPairView):
    """用户登录视图（使用JWT）"""
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        # 先获取登录响应
        response = super().post(request, *args, **kwargs)
        
        # 检查登录是否成功
        if response.status_code == status.HTTP_200_OK:
            try:
                # 从请求数据中获取用户名/学号
                username_or_student_id = request.data.get('username')
                if not username_or_student_id:
                    print("Error: Username/student_id not found in request data")
                    return response
                    
                # 尝试通过用户名查找用户
                try:
                    user_with_profile = User.objects.select_related('profile').get(username=username_or_student_id)
                except User.DoesNotExist:
                    # 用户名查找失败，尝试通过学号查找
                    try:
                        profile = UserProfile.objects.select_related('user').get(student_id=username_or_student_id)
                        user_with_profile = profile.user
                    except UserProfile.DoesNotExist:
                        print(f"Error: User not found for username/student_id: {username_or_student_id}")
                        return response
                
                # 序列化用户信息
                user_serializer = UserSerializer(user_with_profile)
                
                # 确保响应包含access令牌
                if 'access' not in response.data:
                    # 如果access令牌不存在，生成一个新的
                    refresh = RefreshToken.for_user(user_with_profile)
                    response.data['access'] = str(refresh.access_token)
                    response.data['refresh'] = str(refresh)
                
                # 添加用户信息到响应
                response.data['user_info'] = user_serializer.data
                
                # 确保用户有profile
                if hasattr(user_with_profile, 'profile'):
                    profile = user_with_profile.profile
                    response.data['role_info'] = {
                        'id': user_with_profile.id,
                        'role': profile.role,
                        'role_display': profile.get_role_display(),
                        'username': user_with_profile.username
                    }
                else:
                    # 如果没有profile，创建一个默认的
                    profile = UserProfile.objects.create(user=user_with_profile, role='student')
                    response.data['role_info'] = {
                        'id': user_with_profile.id,
                        'role': profile.role,
                        'role_display': profile.get_role_display(),
                        'username': user_with_profile.username
                    }
            except User.DoesNotExist:
                print(f"Error: User not found for username: {username}")
            except Exception as e:
                # 如果出现错误，记录但不影响登录功能
                print(f"Error adding user info to login response: {e}")
        
        return response


class UserProfileView(generics.RetrieveUpdateAPIView):
    """用户个人信息视图"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # 使用select_related预加载profile信息，避免N+1查询
        return User.objects.select_related('profile').get(id=self.request.user.id)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_role(request):
    """获取用户角色信息"""
    try:
        profile = request.user.profile
        return Response({
            'id': request.user.id,
            'role': profile.role,
            'role_display': profile.get_role_display(),
            'username': request.user.username
        })
    except UserProfile.DoesNotExist:
        # 如果用户没有profile，创建一个默认的
        profile = UserProfile.objects.create(user=request.user, role='student')
        return Response({
            'id': request.user.id,
            'role': profile.role,
            'role_display': profile.get_role_display(),
            'username': request.user.username
        })


class UserListView(generics.ListAPIView):
    """用户列表视图（管理员使用）"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """用户详情视图（管理员使用）"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]