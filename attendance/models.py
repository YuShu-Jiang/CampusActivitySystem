from django.db import models
from enrollments.models import Enrollment


class Attendance(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='attendance',
                                      verbose_name='报名记录')
    checkin_time = models.DateTimeField(auto_now_add=True, verbose_name='签到时间')
    checkin_method = models.CharField(max_length=20, default='qr_code', choices=[
        ('qr_code', '二维码'),
        ('manual', '手动'),
    ], verbose_name='签到方式')
    device_info = models.CharField(max_length=255, blank=True, null=True, verbose_name='设备信息')
    ip_address = models.CharField(max_length=50, blank=True, null=True, verbose_name='IP地址')
    qr_token = models.CharField(max_length=100, blank=True, null=True, verbose_name='二维码令牌')

    class Meta:
        db_table = 'attendance'
        verbose_name = '签到记录'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.checkin_time}"