from django.db import models
from django.contrib.auth.models import User


class Activity(models.Model):
    STATUS_CHOICES = (
        ('published', '已发布'),
        ('ongoing', '进行中'),
        ('cancelled', '已取消'),
        ('completed', '已结束'),
    )

    CATEGORY_CHOICES = (
        ('academic', '学术讲座'),
        ('cultural', '文艺表演'),
        ('sports', '体育竞赛'),
        ('volunteer', '志愿服务'),
        ('competition', '创新大赛'),
        ('other', '其他'),
    )

    title = models.CharField(max_length=200, verbose_name='活动标题')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name='活动类别')
    description = models.TextField(verbose_name='活动描述')
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_activities',
                                  verbose_name='组织者')
    location = models.CharField(max_length=200, verbose_name='活动地点')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    registration_deadline = models.DateTimeField(verbose_name='报名截止时间')
    max_participants = models.IntegerField(default=0, verbose_name='最大参与人数')
    current_participants = models.IntegerField(default=0, verbose_name='当前报名人数')
    cover_image = models.ImageField(upload_to='activity_covers/', blank=True, null=True, verbose_name='封面图片')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'activity'
        verbose_name = '活动'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.title