from fastapi import APIRouter, Depends

from app.application.notification_service import NotificationService
from app.presentation.api.v1.schemas import NotificationResponse
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.services import get_notification_service
from vault_shared.db.models import User

notifications_router = APIRouter(tags=["notifications"])


@notifications_router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationResponse]:
    notifications = service.list_for_user(user.id, organization_id=user.organization_id)
    return [NotificationResponse.from_model(n) for n in notifications]
