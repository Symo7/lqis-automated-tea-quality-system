def role_flags(request):
    user = request.user
    if not user.is_authenticated:
        return {"is_admin_role": False, "is_inspector_role": False, "is_supervisor_role": False}

    names = set(user.groups.values_list("name", flat=True))
    return {
        "is_admin_role": user.is_superuser or "Admin" in names,
        "is_inspector_role": user.is_superuser or "Inspector" in names,
        "is_supervisor_role": user.is_superuser or "Supervisor" in names,
    }
