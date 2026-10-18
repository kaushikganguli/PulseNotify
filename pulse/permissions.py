from rest_framework.permissions import BasePermission
from .models import UserProfile
class IsAdminUser(BasePermission):
    message = "Administrator access is required."
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        try:
            return user.profile.role == UserProfile.Role.ADMIN
        except UserProfile.DoesNotExist:
            return False
