from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

def home_view(request):
    """网站首页"""
    context = {
        'title': '校园活动报名与出勤签到系统',
        'version': '1.0.0',
        'author': '蒋东升',
        'student_id': '2402010330',
    }
    return render(request, 'home.html', context)

@api_view(['GET'])
def api_root_view(request):
    """API根路径视图"""
    return Response({
        'message': '校园活动报名与出勤签到系统API',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/api/auth/',
            'activities': '/api/activities/',
            'enrollments': '/api/enrollments/',
            'attendance': '/api/attendance/'
        }
    })