"""
生产环境设置
"""
from .settings import *
import os

# 安全设置
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-production-secret-key')
ALLOWED_HOSTS = ['your-domain.com', 'localhost', '127.0.0.1']

# 数据库设置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'campus_activity_prod'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
    }
}

# 静态文件
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 安全中间件
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# CORS设置
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://your-domain.com',
    'https://your-domain.com',
]