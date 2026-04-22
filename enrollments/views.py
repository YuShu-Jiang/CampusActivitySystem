from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Enrollment
from .serializers import EnrollmentSerializer
from activities.models import Activity
from django.utils import timezone
import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404


class EnrollmentListView(generics.ListCreateAPIView):
    """报名列表和创建视图"""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 普通用户只能看到自己的报名记录
        if not self.request.user.is_staff:
            queryset = Enrollment.objects.filter(user=self.request.user)
        else:
            # 管理员可以看到所有报名记录
            queryset = Enrollment.objects.all()
        
        # 过滤活动
        activity_id = self.request.query_params.get('activity')
        if activity_id:
            try:
                activity_id = int(activity_id)
                queryset = queryset.filter(activity_id=activity_id)
            except ValueError:
                pass
        
        return queryset

    def create(self, request, *args, **kwargs):
        activity_id = request.data.get('activity_id') or request.data.get('activity')
        user_id = request.data.get('user_id', request.user.id)

        try:
            activity = Activity.objects.get(id=activity_id)
        except Activity.DoesNotExist:
            return Response(
                {"error": "活动不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 检查活动状态
        now = timezone.now()
        if now > activity.registration_deadline:
            return Response(
                {"error": "活动报名已截止"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if activity.status != 'published':
            return Response(
                {"error": "活动未开放报名"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查名额
        if activity.max_participants > 0 and activity.current_participants >= activity.max_participants:
            return Response(
                {"error": "活动名额已满"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查是否已报名（包括所有状态）
        if Enrollment.objects.filter(user_id=user_id, activity_id=activity_id).exists():
            # 检查是否有已取消的报名记录
            cancelled_enrollment = Enrollment.objects.filter(
                user_id=user_id, 
                activity_id=activity_id, 
                status='cancelled'
            ).first()
            
            if cancelled_enrollment:
                # 如果是已取消的报名，可以重新报名
                cancelled_enrollment.status = 'registered'
                cancelled_enrollment.save()
                
                # 更新活动报名人数
                activity.current_participants += 1
                activity.save()
                
                serializer = self.get_serializer(cancelled_enrollment)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": "您已报名此活动"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 创建报名记录
        enrollment = Enrollment.objects.create(
            user_id=user_id,
            activity=activity,
            status='registered'
        )

        # 更新活动报名人数
        activity.current_participants += 1
        activity.save()

        serializer = self.get_serializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """报名详情视图"""
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        enrollment = super().get_object()
        # 用户只能操作自己的报名记录（除非是管理员）
        if enrollment.user != self.request.user and not self.request.user.is_staff:
            self.permission_denied(self.request, message="无权操作此报名记录")
        return enrollment

    def destroy(self, request, *args, **kwargs):
        enrollment = self.get_object()
        activity = enrollment.activity

        # 取消报名逻辑
        enrollment.status = 'cancelled'
        enrollment.save()

        # 更新活动报名人数
        if activity.current_participants > 0:
            activity.current_participants -= 1
            activity.save()

        return Response({"message": "报名已取消"}, status=status.HTTP_200_OK)


class ExportEnrollmentsView(APIView):
    """导出活动报名名单"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, activity_id):
        try:
            # 获取活动
            activity = get_object_or_404(Activity, id=activity_id)

            # 验证权限：只有活动组织者或管理员可以导出
            if not (request.user == activity.organizer or request.user.is_staff):
                return Response(
                    {"error": "无权导出此活动的报名名单"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 获取该活动的所有有效报名记录，使用select_related预加载相关数据，避免N+1查询
            enrollments = Enrollment.objects.filter(
                activity=activity,
                status='registered'
            ).select_related('user').order_by('enrollment_time')

            # 创建CSV响应，添加BOM标记以避免Excel乱码
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            # 添加BOM标记
            response.write('\ufeff')
            # 处理文件名中的特殊字符
            safe_title = activity.title.replace('/', '').replace('\\', '').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
            response['Content-Disposition'] = f'attachment; filename="报名名单_{safe_title}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

            writer = csv.writer(response)
            # 写入CSV表头
            writer.writerow(['序号', '用户名', '真实姓名', '学号', '报名时间'])

            # 写入报名记录
            for i, enrollment in enumerate(enrollments, 1):
                # 安全获取用户信息
                username = enrollment.user.username if enrollment.user else ''
                real_name = ''
                student_id = ''
                
                # 检查用户是否有profile
                if hasattr(enrollment.user, 'profile'):
                    profile = enrollment.user.profile
                    real_name = getattr(profile, 'real_name', '')
                    student_id = getattr(profile, 'student_id', '')
                
                # 安全获取报名时间
                enrollment_time = ''
                if hasattr(enrollment, 'enrollment_time') and enrollment.enrollment_time:
                    enrollment_time = enrollment.enrollment_time.strftime('%Y-%m-%d %H:%M:%S')
                
                writer.writerow([
                    i,
                    username,
                    real_name,
                    student_id,
                    enrollment_time
                ])

            return response
        except Exception as e:
            print(f"导出报名名单失败: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"导出报名名单失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )