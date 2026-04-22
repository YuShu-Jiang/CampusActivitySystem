from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('student', '学生'),
        ('organizer', '活动组织者'),
        ('admin', '系统管理员'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    student_id = models.CharField(max_length=20, unique=True, verbose_name='学号')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='电话')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', verbose_name='角色')
    college = models.CharField(max_length=100, blank=True, null=True, verbose_name='学院')
    major = models.CharField(max_length=100, blank=True, null=True, verbose_name='专业')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')

    class Meta:
        db_table = 'user_profile'
        verbose_name = '用户扩展信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# 创建用户时自动创建UserProfile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # 为新用户提供默认的student_id（使用用户名+随机数）
        import random
        default_student_id = f"{instance.username}{random.randint(1000, 9999)}"
        UserProfile.objects.get_or_create(user=instance, defaults={'student_id': default_student_id})


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()