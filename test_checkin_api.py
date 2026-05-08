#!/usr/bin/env python
import os
import sys
import django
import random

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.core.cache import cache
from django.test import RequestFactory
from django.contrib.auth.models import User
from activities.models import Activity
from enrollments.models import Enrollment
from attendance.models import Attendance
from attendance.views import QRCodeGenerateView, QRCodeCheckinView
from rest_framework_simplejwt.tokens import RefreshToken

SUCCESS = "[PASS]"
FAILED = "[FAIL]"

def get_tokens(user):
    """获取用户的JWT令牌"""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }

def test_normal_checkin():
    """测试1：正常签到"""
    print("\n=== Test 1: Normal Checkin ===")
    
    # 获取用户
    try:
        student = User.objects.get(username='001')
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        print(FAILED, "User not found")
        return False
    
    # 获取或创建活动
    activity = Activity.objects.filter(status='published').first()
    if not activity:
        print(FAILED, "No published activity found")
        return False
    
    # 确保活动时间有效
    if activity.start_time > timezone.now() or activity.end_time < timezone.now():
        print(FAILED, "Activity time is not valid")
        return False
    
    # 确保学生已报名
    enrollment, _ = Enrollment.objects.get_or_create(
        user=student,
        activity=activity,
        defaults={'status': 'registered'}
    )
    
    # 删除已有的签到记录
    Attendance.objects.filter(enrollment=enrollment).delete()
    
    # 创建请求工厂
    factory = RequestFactory()
    
    # 生成二维码（使用管理员身份）
    admin_tokens = get_tokens(admin)
    request = factory.post(
        '/api/attendance/generate-qrcode/',
        {'activity_id': activity.id},
        HTTP_AUTHORIZATION=f'Bearer {admin_tokens["access"]}'
    )
    request.user = admin
    
    generate_view = QRCodeGenerateView.as_view()
    response = generate_view(request)
    
    if response.status_code != 200:
        print(FAILED, f"Failed to generate QR code: {response.status_code}")
        return False
    
    qr_data = response.data
    print("Activity ID:", activity.id)
    print("Activity Title:", activity.title)
    print("Checkin Token:", qr_data['token'])
    
    # 执行签到（使用学生身份）
    student_tokens = get_tokens(student)
    device_id = f"test_device_{random.randint(1000, 9999)}"
    request = factory.post(
        '/api/attendance/checkin/',
        {
            'activity_id': activity.id,
            'token': qr_data['token'],
            'device_id': device_id
        },
        HTTP_AUTHORIZATION=f'Bearer {student_tokens["access"]}'
    )
    request.user = student
    
    checkin_view = QRCodeCheckinView.as_view()
    response = checkin_view(request)
    
    if response.status_code == 200:
        print(SUCCESS, "Normal checkin successful")
        print("Response:", response.data)
        return True
    else:
        print(FAILED, f"Normal checkin failed: {response.status_code} - {response.data}")
        return False

def test_token_burn():
    """测试2：令牌即焚（同一令牌只能使用一次）"""
    print("\n=== Test 2: Token Burn (One-time Use) ===")
    
    try:
        student = User.objects.get(username='001')
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        print(FAILED, "User not found")
        return False
    
    activity = Activity.objects.filter(status='published').first()
    if not activity:
        print(FAILED, "No published activity found")
        return False
    
    enrollment, _ = Enrollment.objects.get_or_create(
        user=student,
        activity=activity,
        defaults={'status': 'registered'}
    )
    Attendance.objects.filter(enrollment=enrollment).delete()
    
    factory = RequestFactory()
    
    # 生成二维码
    admin_tokens = get_tokens(admin)
    request = factory.post(
        '/api/attendance/generate-qrcode/',
        {'activity_id': activity.id},
        HTTP_AUTHORIZATION=f'Bearer {admin_tokens["access"]}'
    )
    request.user = admin
    
    generate_view = QRCodeGenerateView.as_view()
    response = generate_view(request)
    if response.status_code != 200:
        print(FAILED, "Failed to generate QR code")
        return False
    
    qr_data = response.data
    device_id = f"test_device_{random.randint(1000, 9999)}"
    
    # 第一次签到
    student_tokens = get_tokens(student)
    request = factory.post(
        '/api/attendance/checkin/',
        {
            'activity_id': activity.id,
            'token': qr_data['token'],
            'device_id': device_id
        },
        HTTP_AUTHORIZATION=f'Bearer {student_tokens["access"]}'
    )
    request.user = student
    
    checkin_view = QRCodeCheckinView.as_view()
    response1 = checkin_view(request)
    if response1.status_code == 200:
        print(SUCCESS, "First checkin successful (token used)")
    else:
        print(FAILED, f"First checkin failed: {response1.status_code} - {response1.data}")
        return False
    
    # 创建新的报名记录用于第二次测试
    Attendance.objects.filter(enrollment=enrollment).delete()
    
    # 第二次使用同一令牌签到（应该失败）
    request = factory.post(
        '/api/attendance/checkin/',
        {
            'activity_id': activity.id,
            'token': qr_data['token'],
            'device_id': device_id + "_2"
        },
        HTTP_AUTHORIZATION=f'Bearer {student_tokens["access"]}'
    )
    request.user = student
    
    response2 = checkin_view(request)
    if response2.status_code == 400 and ("过期或无效" in response2.data.get('error', '')):
        print(SUCCESS, "Second checkin failed, token destroyed (token burn works)")
        print("Response:", response2.data)
        return True
    else:
        print(FAILED, f"Token burn test failed, second checkin should fail: {response2.status_code} - {response2.data}")
        return False

def test_device_conflict():
    """测试3：设备冲突（同一设备在同一活动中只能签到一次）"""
    print("\n=== Test 3: Device Conflict ===")
    
    try:
        student1 = User.objects.get(username='001')
        student2 = User.objects.get(username='002')
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        print(FAILED, "User not found")
        return False
    
    activity = Activity.objects.filter(status='published').first()
    if not activity:
        print(FAILED, "No published activity found")
        return False
    
    enrollment1, _ = Enrollment.objects.get_or_create(
        user=student1,
        activity=activity,
        defaults={'status': 'registered'}
    )
    enrollment2, _ = Enrollment.objects.get_or_create(
        user=student2,
        activity=activity,
        defaults={'status': 'registered'}
    )
    Attendance.objects.filter(enrollment__activity=activity).delete()
    
    factory = RequestFactory()
    
    # 生成第一个二维码
    admin_tokens = get_tokens(admin)
    request = factory.post(
        '/api/attendance/generate-qrcode/',
        {'activity_id': activity.id},
        HTTP_AUTHORIZATION=f'Bearer {admin_tokens["access"]}'
    )
    request.user = admin
    
    generate_view = QRCodeGenerateView.as_view()
    response = generate_view(request)
    if response.status_code != 200:
        print(FAILED, "Failed to generate QR code")
        return False
    
    qr_data = response.data
    device_id = f"shared_device_{random.randint(1000, 9999)}"
    
    # 学生1使用设备签到
    student1_tokens = get_tokens(student1)
    request = factory.post(
        '/api/attendance/checkin/',
        {
            'activity_id': activity.id,
            'token': qr_data['token'],
            'device_id': device_id
        },
        HTTP_AUTHORIZATION=f'Bearer {student1_tokens["access"]}'
    )
    request.user = student1
    
    checkin_view = QRCodeCheckinView.as_view()
    response1 = checkin_view(request)
    if response1.status_code == 200:
        print(SUCCESS, "Student 1 checkin with device successful")
    else:
        print(FAILED, f"Student 1 checkin failed: {response1.status_code} - {response1.data}")
        return False
    
    # 生成第二个二维码
    request = factory.post(
        '/api/attendance/generate-qrcode/',
        {'activity_id': activity.id},
        HTTP_AUTHORIZATION=f'Bearer {admin_tokens["access"]}'
    )
    request.user = admin
    
    response = generate_view(request)
    if response.status_code != 200:
        print(FAILED, "Failed to generate second QR code")
        return False
    
    qr_data2 = response.data
    
    # 学生2使用同一设备签到（应该失败）
    student2_tokens = get_tokens(student2)
    request = factory.post(
        '/api/attendance/checkin/',
        {
            'activity_id': activity.id,
            'token': qr_data2['token'],
            'device_id': device_id
        },
        HTTP_AUTHORIZATION=f'Bearer {student2_tokens["access"]}'
    )
    request.user = student2
    
    response2 = checkin_view(request)
    if response2.status_code == 400 and "该设备已在此活动中签到" in response2.data.get('error', ''):
        print(SUCCESS, "Student 2 checkin with same device failed (device conflict works)")
        print("Response:", response2.data)
        return True
    else:
        print(FAILED, f"Device conflict test failed: {response2.status_code} - {response2.data}")
        return False

def test_token_expiry():
    """测试4：令牌过期（10分钟有效期）"""
    print("\n=== Test 4: Token Expiry ===")
    
    try:
        student = User.objects.get(username='001')
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        print(FAILED, "User not found")
        return False
    
    activity = Activity.objects.filter(status='published').first()
    if not activity:
        print(FAILED, "No published activity found")
        return False
    
    enrollment, _ = Enrollment.objects.get_or_create(
        user=student,
        activity=activity,
        defaults={'status': 'registered'}
    )
    Attendance.objects.filter(enrollment=enrollment).delete()
    
    factory = RequestFactory()
    
    # 生成二维码
    admin_tokens = get_tokens(admin)
    request = factory.post(
        '/api/attendance/generate-qrcode/',
        {'activity_id': activity.id},
        HTTP_AUTHORIZATION=f'Bearer {admin_tokens["access"]}'
    )
    request.user = admin
    
    generate_view = QRCodeGenerateView.as_view()
    response = generate_view(request)
    if response.status_code != 200:
        print(FAILED, "Failed to generate QR code")
        return False
    
    qr_data = response.data
    
    # 手动删除缓存中的令牌（模拟过期）
    cache_key = f"qr_token_{activity.id}_{qr_data['token']}"
    cache.delete(cache_key)
    print(SUCCESS, "Manually deleted cached token (simulating expiry)")
    
    # 尝试使用已过期的令牌签到
    student_tokens = get_tokens(student)
    device_id = f"test_device_{random.randint(1000, 9999)}"
    request = factory.post(
        '/api/attendance/checkin/',
        {
            'activity_id': activity.id,
            'token': qr_data['token'],
            'device_id': device_id
        },
        HTTP_AUTHORIZATION=f'Bearer {student_tokens["access"]}'
    )
    request.user = student
    
    checkin_view = QRCodeCheckinView.as_view()
    response = checkin_view(request)
    
    if response.status_code == 400 and "过期或无效" in response.data.get('error', ''):
        print(SUCCESS, "Token expiry test successful, expired token cannot checkin")
        print("Response:", response.data)
        return True
    else:
        print(FAILED, f"Token expiry test failed: {response.status_code} - {response.data}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Campus Activity Checkin System - API Test Script")
    print("Testing four checkin scenarios:")
    print("1. Normal Checkin")
    print("2. Token Burn (one-time use)")
    print("3. Device Conflict")
    print("4. Token Expiry (10 minutes)")
    print("=" * 60)
    
    results = []
    
    results.append(("Normal Checkin", test_normal_checkin()))
    results.append(("Token Burn", test_token_burn()))
    results.append(("Device Conflict", test_device_conflict()))
    results.append(("Token Expiry", test_token_expiry()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = SUCCESS if result else FAILED
        print(f"{test_name}: {status}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed, please check the code logic")
        sys.exit(1)