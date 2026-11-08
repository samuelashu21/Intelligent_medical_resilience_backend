from apps.audit.models import AuditEvent


def get_client_ip(request):
    """
    Extract the client IP address.

    Trust forwarded headers only when the application is behind
    a correctly configured trusted reverse proxy.
    """

    if request is None:
        return None

    return request.META.get("REMOTE_ADDR")
 

def record_audit_event(
    *,
    actor=None,
    category,
    action,
    target_type,
    target_id="",
    description="",
    organization=None,
    facility=None,
    changes=None,
    metadata=None,
    request=None,
):
    """
    Create an audit event for an administrative or security action.
    """

    ip_address = get_client_ip(request)

    user_agent = ""

    if request is not None:
        user_agent = request.META.get(
            "HTTP_USER_AGENT",
            "",
        )[:2000]

    return AuditEvent.objects.create(
        actor=actor,
        category=category,
        action=action,
        target_type=target_type,
        target_id=str(target_id or ""),
        description=description,
        organization=organization,
        facility=facility,
        changes=changes or {},
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
    ) 