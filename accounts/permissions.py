from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy

from .models import RoleChoices


def has_role(user, *roles):
    return bool(user and user.is_authenticated and user.role in roles)


def is_super_admin(user):
    return has_role(user, RoleChoices.SUPER_ADMIN)


def is_department_admin(user):
    return has_role(user, RoleChoices.DEPARTMENT_ADMIN)


def get_user_department(user):
    if is_department_admin(user):
        return user.department
    return None


def ensure_department_assignment(user):
    if is_department_admin(user) and user.department is None:
        raise PermissionDenied("Department admin account is not assigned to a department.")


def filter_by_department_ownership(queryset, user, department_field="department"):
    ensure_department_assignment(user)
    department = get_user_department(user)
    if department is None:
        return queryset
    return queryset.filter(**{department_field: department})


def super_admin_required(view_func):
    @login_required(login_url=reverse_lazy("accounts:login"))
    @user_passes_test(is_super_admin, login_url=reverse_lazy("accounts:login"))
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def department_admin_required(view_func):
    @login_required(login_url=reverse_lazy("accounts:login"))
    @user_passes_test(is_department_admin, login_url=reverse_lazy("accounts:login"))
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        ensure_department_assignment(request.user)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


class PortalLoginRequiredMixin(LoginRequiredMixin):
    login_url = reverse_lazy("accounts:login")


class RoleRequiredMixin(PortalLoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()

    def test_func(self):
        return has_role(self.request.user, *self.allowed_roles)


class SuperAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (RoleChoices.SUPER_ADMIN,)


class DepartmentAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (RoleChoices.DEPARTMENT_ADMIN,)

    def dispatch(self, request, *args, **kwargs):
        ensure_department_assignment(request.user)
        return super().dispatch(request, *args, **kwargs)


class DepartmentScopedQuerysetMixin(RoleRequiredMixin):
    allowed_roles = (RoleChoices.SUPER_ADMIN, RoleChoices.DEPARTMENT_ADMIN)
    department_field = "department"

    def dispatch(self, request, *args, **kwargs):
        ensure_department_assignment(request.user)
        return super().dispatch(request, *args, **kwargs)

    def scope_to_user_department(self, queryset):
        return filter_by_department_ownership(
            queryset,
            self.request.user,
            department_field=self.department_field,
        )
