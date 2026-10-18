import os
from .base import *
DEBUG = False
if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY must be configured in production.")
if "*" in ALLOWED_HOSTS:
    raise RuntimeError("Wildcard ALLOWED_HOSTS is not allowed in production.")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
