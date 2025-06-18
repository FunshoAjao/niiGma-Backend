from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from rest_framework import permissions

class IsSuperAdmin(BasePermission):
    """
    Allows access only to SuperAdmin or Django superuser.
    """
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        if request.method in permissions.SAFE_METHODS:
            return True
        
        raise PermissionDenied("You do not have the required role to access this resource.")

class IsCouncilOrStaffAdmin(BasePermission):
    """
    Allows access to users who are Admin, Contractor, Staff, SuperAdmin, or Superuser.
    """
    def has_permission(self, request, view):
        user = request.user
        allowed_roles = [
            RoleType.Admin,
            RoleType.Contractor,
            RoleType.Staff,
            RoleType.SuperAdmin,
        ]
        if getattr(user, "is_superuser", False) or getattr(user, "role", None) in allowed_roles:
            return True

        raise PermissionDenied("You do not have the required role to access this resource.")