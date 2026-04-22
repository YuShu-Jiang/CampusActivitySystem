from django.db import models
from django.contrib.auth.models import User
from activities.models import Activity


class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments', verbose_name='用户')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='enrollments', verbose_name='活动')
    enrollment_time = models.DateTimeField(auto_now_add=True, verbose_name='报名时间')
    status = models.CharField(max_length=20, default='registered', choices=[
        ('registered', '已报名'),
        ('cancelled', '已取消'),
        ('attended', '已参加'),
    ], verbose_name='状态')
    notes = models.TextField(blank=True, null=True, verbose_name='备注')

    class Meta:
        db_table = 'enrollment'
        verbose_name = '报名记录'
        verbose_name_plural = verbose_name
        unique_together = ['user', 'activity']  # 防止重复报名

    def __str__(self):
        return f"{self.user.username} - {self.activity.title}"