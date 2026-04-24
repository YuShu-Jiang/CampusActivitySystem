from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
import secrets
import qrcode
import io
import base64
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.cache import cache
from .models import Attendance
from .serializers import AttendanceSerializer
from enrollments.models import Enrollment
from activities.models import Activity


class QRCodeGenerateView(APIView):
    """生成活动签到二维码"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        activity_id = request.data.get('activity_id')

        try:
            activity = Activity.objects.get(id=activity_id)
        except Activity.DoesNotExist:
            return Response(
                {"error": "活动不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 验证用户是否有权限（活动组织者或管理员）
        if activity.organizer != request.user and not request.user.is_staff:
            return Response(
                {"error": "无权生成此活动的签到二维码"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 检查活动是否正在进行
        now = timezone.now()
        if now < activity.start_time:
            return Response(
                {"error": "活动尚未开始"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if now > activity.end_time:
            return Response(
                {"error": "活动已结束"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生成唯一令牌（有效时间10分钟，6位）
        token = secrets.token_hex(3)  # 6位十六进制字符串
        expiry_time = now + timedelta(minutes=10)
        
        # 将令牌存储到缓存中，设置10分钟过期时间
        cache_key = f"qr_token_{activity_id}_{token}"
        cache.set(cache_key, True, 600)  # 600秒 = 10分钟

        # 生成二维码
        checkin_url = f"http://127.0.0.1:8000/api/attendance/checkin/?activity_id={activity_id}&token={token}"

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(checkin_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # 转换为base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            qr_code_base64 = f"data:image/png;base64,{img_str}"
        except Exception as e:
            print(f"生成二维码失败: {e}")
            return Response(
                {"error": "生成二维码失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 返回响应
        return Response({
            'token': token,
            'expiry_time': expiry_time,
            'qr_code': qr_code_base64,
            'checkin_url': checkin_url,
            'activity_id': activity_id,
            'activity_title': activity.title
        }, status=status.HTTP_200_OK)


class QRCodeCheckinView(APIView):
    """二维码签到"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        activity_id = request.data.get('activity_id')

        if not token or not activity_id:
            return Response(
                {"error": "缺少必要参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            activity = Activity.objects.get(id=activity_id)
        except Activity.DoesNotExist:
            return Response(
                {"error": "活动不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 验证令牌是否有效
        cache_key = f"qr_token_{activity_id}_{token}"
        if not cache.get(cache_key):
            return Response(
                {"error": "二维码已过期或无效"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查用户是否已报名
        enrollment = Enrollment.objects.filter(
            user=request.user,
            activity=activity,
            status='registered'
        ).first()

        if not enrollment:
            return Response(
                {"error": "您未报名此活动"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查是否已签到
        if Attendance.objects.filter(enrollment=enrollment).exists():
            return Response(
                {"error": "您已签到，请勿重复操作"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建签到记录
        attendance = Attendance.objects.create(
            enrollment=enrollment,
            checkin_method='qr_code',
            device_info=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=self.get_client_ip(request),
            qr_token=token
        )
        
        # 签到成功后删除令牌，确保每个令牌只能使用一次
        cache_key = f"qr_token_{activity_id}_{token}"
        cache.delete(cache_key)

        return Response({
            'success': True,
            'message': '签到成功',
            'checkin_time': attendance.checkin_time,
            'activity_title': activity.title
        }, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AttendanceListView(generics.ListAPIView):
    """签到记录列表"""
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 获取当前用户
        user = self.request.user
        queryset = Attendance.objects.all()
        
        # 应用筛选条件
        activity_id = self.request.query_params.get('activity_id')
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        
        if activity_id:
            queryset = queryset.filter(enrollment__activity_id=activity_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if search:
            queryset = queryset.filter(enrollment__user__username__icontains=search) | \
                      queryset.filter(enrollment__user__student_profile__student_id__icontains=search)
        
        # 权限过滤
        if not user.is_staff and not hasattr(user, 'organizer_profile'):
            queryset = queryset.filter(enrollment__user=user)
        elif hasattr(user, 'organizer_profile'):
            queryset = queryset.filter(enrollment__activity__organizer=user)
        
        return queryset


class ManualCheckinView(APIView):
    """手动签到视图"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        activity_id = request.data.get('activity_id')
        user_id = request.data.get('user_id')
        enrollment_id = request.data.get('enrollment_id')
        student_id = request.data.get('student_id')

        if not activity_id:
            return Response(
                {"error": "缺少活动ID"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 至少需要提供一个用户标识
        if not user_id and not enrollment_id and not student_id:
            return Response(
                {"error": "缺少用户标识，请提供user_id、enrollment_id或student_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 获取活动
            activity = Activity.objects.get(id=activity_id)
        except Activity.DoesNotExist:
            return Response(
                {"error": "活动不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 验证用户权限（活动组织者或管理员）
        user = request.user
        if activity.organizer != user and not user.is_staff:
            return Response(
                {"error": "无权操作此活动"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 根据不同参数获取报名记录
        enrollment = None
        if enrollment_id:
            # 通过enrollment_id获取
            try:
                enrollment = Enrollment.objects.get(id=enrollment_id, activity=activity, status='registered')
            except Enrollment.DoesNotExist:
                return Response(
                    {"error": "报名记录不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif user_id:
            # 通过user_id获取
            try:
                student = User.objects.get(id=user_id)
                enrollment = Enrollment.objects.get(user=student, activity=activity, status='registered')
            except User.DoesNotExist:
                return Response(
                    {"error": "用户不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Enrollment.DoesNotExist:
                return Response(
                    {"error": "该学生未报名此活动"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif student_id:
            # 通过学号获取
            try:
                from users.models import UserProfile
                user_profile = UserProfile.objects.get(student_id=student_id)
                enrollment = Enrollment.objects.get(user=user_profile.user, activity=activity, status='registered')
            except UserProfile.DoesNotExist:
                return Response(
                    {"error": "学号不存在"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Enrollment.DoesNotExist:
                return Response(
                    {"error": "该学生未报名此活动"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 检查是否已签到
        if Attendance.objects.filter(enrollment=enrollment).exists():
            return Response(
                {"error": "该学生已签到"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建签到记录
        attendance = Attendance.objects.create(
            enrollment=enrollment,
            checkin_method='manual',
            device_info='manual_checkin',
            ip_address=self.get_client_ip(request)
        )

        return Response({
            'success': True,
            'message': '手动签到成功',
            'checkin_time': attendance.checkin_time
        }, status=status.HTTP_200_OK)


class AttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """考勤记录详情视图"""
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Attendance.objects.all()

    def get_object(self):
        attendance = super().get_object()
        user = self.request.user
        activity = attendance.enrollment.activity
        
        # 验证用户权限
        if activity.organizer != user and not user.is_staff:
            self.permission_denied(self.request, message="无权操作此考勤记录")
            
        return attendance

    def destroy(self, request, *args, **kwargs):
        attendance = self.get_object()
        attendance.delete()
        return Response({
            "success": True,
            "message": "考勤记录删除成功"
        }, status=status.HTTP_200_OK)


class ActivityAttendanceView(APIView):
    """获取活动的所有报名人员，包括已签到和未签到的"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        activity_id = request.query_params.get('activity_id')
        
        if not activity_id:
            return Response(
                {"error": "缺少活动ID"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            activity = Activity.objects.get(id=activity_id)
        except Activity.DoesNotExist:
            return Response(
                {"error": "活动不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 验证用户权限（活动组织者或管理员）
        user = request.user
        if activity.organizer != user and not user.is_staff:
            return Response(
                {"error": "无权操作此活动"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 获取活动的所有有效报名记录
        enrollments = Enrollment.objects.filter(
            activity=activity,
            status='registered'
        ).select_related('user__profile').order_by('user__username')
        
        # 获取活动的所有签到记录
        attendance_records = Attendance.objects.filter(
            enrollment__activity=activity
        ).select_related('enrollment__user')
        
        # 创建签到记录映射，方便后续查询
        attendance_map = {}
        for attendance in attendance_records:
            attendance_map[attendance.enrollment.id] = attendance
        
        # 准备返回数据
        result = []
        for enrollment in enrollments:
            attendance = attendance_map.get(enrollment.id)
            
            if attendance:
                # 已签到
                record = {
                    'id': attendance.id,
                    'activity_id': activity.id,
                    'activity_title': activity.title,
                    'user_id': enrollment.user.id,
                    'enrollment_id': enrollment.id,
                    'student_id': enrollment.user.profile.student_id if hasattr(enrollment.user, 'profile') else '',
                    'student_name': enrollment.user.username,
                    'checkin_time': attendance.checkin_time,
                    'checkin_method': attendance.checkin_method,
                    'status': 'checked_in'
                }
            else:
                # 未签到
                record = {
                    'id': None,
                    'activity_id': activity.id,
                    'activity_title': activity.title,
                    'user_id': enrollment.user.id,
                    'enrollment_id': enrollment.id,
                    'student_id': enrollment.user.profile.student_id if hasattr(enrollment.user, 'profile') else '',
                    'student_name': enrollment.user.username,
                    'checkin_time': None,
                    'checkin_method': None,
                    'status': 'not_checked_in'
                }
            
            result.append(record)
        
        return Response(result, status=status.HTTP_200_OK)


class AttendanceRootView(APIView):
    """Attendance API 根路径视图"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'message': '校园活动报名与出勤签到系统 - 考勤API',
            'version': '1.0.0',
            'endpoints': {
                'generate-qrcode': '/api/attendance/generate-qrcode/',
                'checkin': '/api/attendance/checkin/',
                'manual-checkin': '/api/attendance/manual-checkin/',
                'records': '/api/attendance/records/',
                'activity-attendance': '/api/attendance/activity-attendance/',
            }
        })