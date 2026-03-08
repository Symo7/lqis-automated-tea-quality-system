from django.contrib.auth.decorators import user_passes_test


def in_group(user, groups: list[str]) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=groups).exists()


def role_required(*groups: str):
    return user_passes_test(lambda user: in_group(user, list(groups)))
