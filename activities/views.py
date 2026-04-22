from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from .models import Activity
from .serializers import ActivitySerializer
from enrollments.models import Enrollment
from attendance.models import Attendance
from django.utils import timezone


class ActivityListView(generics.ListCreateAPIView):
    """活动列表和创建视图"""
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'organizer', 'location']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['start_time', 'created_at', 'current_participants']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)


class ActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """活动详情视图"""
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_object(self):
        activity = super().get_object()
        # 只有活动创建者或管理员可以修改/删除
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if activity.organizer != self.request.user and not self.request.user.is_staff:
                self.permission_denied(self.request, message="无权操作此活动")
        return activity


class UpcomingActivitiesView(generics.ListAPIView):
    """即将开始的活动列表"""
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        return Activity.objects.filter(
            status='published',
            start_time__gt=now
        ).order_by('start_time')


class MyActivitiesView(generics.ListAPIView):
    """我创建的活动"""
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.filter(organizer=self.request.user)


class OrganizerStatsView(generics.GenericAPIView):
    """组织者统计数据视图"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 获取当前用户创建的所有活动
        activities = Activity.objects.filter(organizer=request.user)
        total_activities = activities.count()
        published_activities = activities.filter(status='published').count()
        
        # 计算总参与人数
        total_participants = Enrollment.objects.filter(
            activity__in=activities,
            status='registered'
        ).count()
        
        # 计算平均签到率
        total_checkin_rate = 0
        activity_count_with_checkin = 0
        
        for activity in activities:
            # 获取活动的报名人数
            enrolled_count = Enrollment.objects.filter(
                activity=activity,
                status='registered'
            ).count()
            
            if enrolled_count > 0:
                # 获取活动的签到人数
                checked_in_count = Attendance.objects.filter(
                    enrollment__activity=activity
                ).count()
                
                # 计算该活动的签到率
                checkin_rate = checked_in_count / enrolled_count
                total_checkin_rate += checkin_rate
                activity_count_with_checkin += 1
        
        average_checkin_rate = 0
        if activity_count_with_checkin > 0:
            average_checkin_rate = total_checkin_rate / activity_count_with_checkin
        
        # 返回统计数据
        stats = {
            'total_activities': total_activities,
            'published_activities': published_activities,
            'total_participants': total_participants,
            'average_checkin_rate': round(average_checkin_rate * 100, 2)  # 转换为百分比
        }
        
        return Response(stats, status=status.HTTP_200_OK)


class PlatformStatsView(generics.GenericAPIView):
    """全平台宏观数据统计视图"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 只有管理员可以查看全平台统计数据
        if not request.user.is_staff:
            return Response(
                {"error": "无权查看全平台统计数据"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 获取日期范围筛选参数
        date_range = request.query_params.get('date_range', 'all')
        now = timezone.now()
        
        if date_range != 'all':
            try:
                date_range = int(date_range)
                start_date = now - timezone.timedelta(days=date_range)
            except ValueError:
                start_date = None
        else:
            start_date = None
        
        # 1. 用户统计
        from django.contrib.auth.models import User
        from users.models import UserProfile
        
        if start_date:
            total_users = User.objects.filter(date_joined__gte=start_date).count()
            total_profiles = UserProfile.objects.filter(user__date_joined__gte=start_date).count()
        else:
            total_users = User.objects.count()
            total_profiles = UserProfile.objects.count()
        
        # 按角色统计用户
        role_stats = {}
        for role_code, role_name in UserProfile.ROLE_CHOICES:
            count = UserProfile.objects.filter(role=role_code).count()
            role_stats[role_code] = {'name': role_name, 'count': count}
        
        # 2. 活动统计
        activities = Activity.objects.all()
        if start_date:
            activities = activities.filter(created_at__gte=start_date)
        
        total_activities = activities.count()
        
        # 按状态统计活动
        status_stats = {}
        for status_code, status_name in Activity.STATUS_CHOICES:
            count = activities.filter(status=status_code).count()
            status_stats[status_code] = {'name': status_name, 'count': count}
        
        # 按类别统计活动
        category_stats = {}
        for category_code, category_name in Activity.CATEGORY_CHOICES:
            count = activities.filter(category=category_code).count()
            category_stats[category_code] = {'name': category_name, 'count': count}
        
        # 3. 报名统计
        enrollments = Enrollment.objects.all()
        if start_date:
            enrollments = enrollments.filter(enrollment_time__gte=start_date)
        
        total_enrollments = enrollments.count()
        registered_enrollments = enrollments.filter(status='registered').count()
        cancelled_enrollments = enrollments.filter(status='cancelled').count()
        
        # 4. 签到统计
        attendances = Attendance.objects.all()
        if start_date:
            attendances = attendances.filter(checkin_time__gte=start_date)
        
        total_checkins = attendances.count()
        
        # 按签到方式统计
        checkin_method_stats = {
            'qr_code': {'name': '二维码签到', 'count': attendances.filter(checkin_method='qr_code').count()},
            'manual': {'name': '手动签到', 'count': attendances.filter(checkin_method='manual').count()}
        }
        
        # 5. 计算活跃度（过去7天内有活动的用户数）
        seven_days_ago = now - timezone.timedelta(days=7)
        active_users = set()
        
        # 过去7天内有报名活动的用户
        try:
            active_enrollments = Enrollment.objects.filter(enrollment_time__gte=seven_days_ago)
            for enrollment in active_enrollments:
                if enrollment.user_id:
                    active_users.add(enrollment.user_id)
        except Exception as e:
            print(f"计算活跃报名用户时出错: {e}")
        
        # 过去7天内有签到的用户
        try:
            active_checkins = Attendance.objects.filter(checkin_time__gte=seven_days_ago).select_related('enrollment')
            for attendance in active_checkins:
                if attendance.enrollment and attendance.enrollment.user_id:
                    active_users.add(attendance.enrollment.user_id)
        except Exception as e:
            print(f"计算活跃签到用户时出错: {e}")
        
        # 过去7天内有组织活动的用户
        try:
            active_organizers = activities.filter(created_at__gte=seven_days_ago)
            for activity in active_organizers:
                if activity.organizer_id:
                    active_users.add(activity.organizer_id)
        except Exception as e:
            print(f"计算活跃组织者时出错: {e}")
        
        active_user_count = len(active_users)
        activity_rate = round(active_user_count / total_users * 100, 2) if total_users > 0 else 0
        
        # 6. 计算签到率
        checkin_rate = round(total_checkins / registered_enrollments * 100, 2) if registered_enrollments > 0 else 0
        
        # 7. 准备图表数据
        # 活动状态分布饼图
        status_labels = [status_stats[code]['name'] for code in status_stats]
        status_data = [status_stats[code]['count'] for code in status_stats]
        
        # 用户角色分布饼图
        role_labels = [role_stats[code]['name'] for code in role_stats]
        role_data = [role_stats[code]['count'] for code in role_stats]
        
        # 活动类别分布柱状图
        category_labels = [category_stats[code]['name'] for code in category_stats]
        category_data = [category_stats[code]['count'] for code in category_stats]
        
        # 签到方式分布饼图
        checkin_method_labels = [checkin_method_stats[code]['name'] for code in checkin_method_stats]
        checkin_method_data = [checkin_method_stats[code]['count'] for code in checkin_method_stats]
        
        # 准备返回数据
        response_data = {
            'overview': {
                'total_users': total_users,
                'total_activities': total_activities,
                'total_enrollments': total_enrollments,
                'total_checkins': total_checkins,
                'active_users': active_user_count,
                'activity_rate': activity_rate,
                'checkin_rate': checkin_rate,
                'registered_enrollments': registered_enrollments,
                'cancelled_enrollments': cancelled_enrollments
            },
            'role_stats': role_stats,
            'status_stats': status_stats,
            'category_stats': category_stats,
            'checkin_method_stats': checkin_method_stats,
            'charts': {
                'status_distribution': {
                    'labels': status_labels,
                    'data': status_data
                },
                'role_distribution': {
                    'labels': role_labels,
                    'data': role_data
                },
                'category_distribution': {
                    'labels': category_labels,
                    'data': category_data
                },
                'checkin_method_distribution': {
                    'labels': checkin_method_labels,
                    'data': checkin_method_data
                }
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class ActivityAnalyticsView(generics.GenericAPIView):
    """活动数据分析视图"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 获取查询参数
        activity_id = request.query_params.get('activity_id')
        date_range = request.query_params.get('date_range', 'all')
        
        # 构建基础查询
        if request.user.is_staff:
            # 管理员可以查看所有活动
            base_activities = Activity.objects.all()
        else:
            # 普通用户只能查看自己组织的活动
            base_activities = Activity.objects.filter(organizer=request.user)
        
        # 按活动筛选
        if activity_id:
            try:
                activity_id = int(activity_id)
                base_activities = base_activities.filter(id=activity_id)
            except ValueError:
                # 如果activity_id不是有效的整数，忽略活动筛选
                pass
        
        # 按日期范围筛选
        now = timezone.now()
        if date_range != 'all':
            try:
                date_range = int(date_range)
                start_date = now - timezone.timedelta(days=date_range)
                base_activities = base_activities.filter(created_at__gte=start_date)
            except ValueError:
                # 如果date_range不是有效的整数，忽略日期范围筛选
                pass
        
        # 获取所有符合条件的活动
        activities = base_activities.all()
        
        # 准备统计数据
        total_activities = activities.count()
        total_participants = 0
        total_checked_in = 0
        total_enrolled = 0
        total_participation_rate = 0
        valid_activity_count = 0
        
        # 准备图表数据
        participation_labels = []
        participation_data = []
        checkin_rate_labels = []
        checkin_rate_data = []
        
        # 准备活动类别分布数据
        category_distribution = {}
        # 准备活动状态分布数据
        status_distribution = {}
        # 准备签到方式分布数据
        checkin_method_distribution = {}
        
        # 准备详情数据
        details = []
        
        for activity in activities:
            # 获取活动的报名人数
            enrolled_count = Enrollment.objects.filter(
                activity=activity,
                status='registered'
            ).count()
            
            # 获取活动的签到人数
            checked_in_count = Attendance.objects.filter(
                enrollment__activity=activity
            ).count()
            
            # 更新活动类别分布
            category = activity.category
            category_distribution[category] = category_distribution.get(category, 0) + 1
            
            # 更新活动状态分布
            status = activity.status
            status_distribution[status] = status_distribution.get(status, 0) + 1
            
            # 更新签到方式分布
            checkin_methods = Attendance.objects.filter(
                enrollment__activity=activity
            ).values_list('checkin_method', flat=True)
            for method in checkin_methods:
                checkin_method_distribution[method] = checkin_method_distribution.get(method, 0) + 1
            
            # 计算参与率和签到率
            participation_rate = 0
            checkin_rate = 0
            
            if enrolled_count > 0:
                checkin_rate = checked_in_count / enrolled_count
                total_checked_in += checked_in_count
                total_enrolled += enrolled_count
            
            # 计算参与率（这里假设参与率是报名人数/最大参与人数）
            if activity.max_participants and activity.max_participants > 0:
                participation_rate = enrolled_count / activity.max_participants
                total_participation_rate += participation_rate
                valid_activity_count += 1
            
            # 更新总计数据
            total_participants += enrolled_count
            
            # 添加图表数据
            participation_labels.append(activity.title[:10] + '...')
            participation_data.append(enrolled_count)
            checkin_rate_labels.append(activity.title[:10] + '...')
            checkin_rate_data.append(round(checkin_rate * 100, 1))
            
            # 添加详情数据
            details.append({
                'activity_id': activity.id,
                'activity_title': activity.title,
                'participant_count': enrolled_count,
                'checkin_count': checked_in_count,
                'participation_rate': participation_rate * 100,
                'checkin_rate': checkin_rate * 100,
                'created_at': activity.created_at.isoformat()
            })
        
        # 计算平均参与率和平均签到率
        average_participation_rate = 0
        if valid_activity_count > 0:
            average_participation_rate = total_participation_rate / valid_activity_count * 100
        
        average_checkin_rate = 0
        if total_enrolled > 0:
            average_checkin_rate = total_checked_in / total_enrolled * 100
        
        # 准备返回数据
        response_data = {
            'stats': {
                'total_activities': total_activities,
                'total_participants': total_participants,
                'average_participation_rate': round(average_participation_rate, 2),
                'average_checkin_rate': round(average_checkin_rate, 2)
            },
            'charts': {
                'participation': {
                    'labels': participation_labels,
                    'data': participation_data
                },
                'checkin_rate': {
                    'labels': checkin_rate_labels,
                    'data': checkin_rate_data
                },
                'category_distribution': {
                    'labels': list(category_distribution.keys()),
                    'data': list(category_distribution.values())
                },
                'status_distribution': {
                    'labels': list(status_distribution.keys()),
                    'data': list(status_distribution.values())
                },
                'checkin_method_distribution': {
                    'labels': list(checkin_method_distribution.keys()),
                    'data': list(checkin_method_distribution.values())
                }
            },
            'details': details
        }
        
        return Response(response_data, status=status.HTTP_200_OK)