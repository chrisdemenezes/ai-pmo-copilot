import logging

from src.database.models import Invitation

logger = logging.getLogger(__name__)


class NoOpNotificationProvider:
    """Logs and does nothing else -- the seam exists, the provider doesn't
    yet (item 6, Convites -- D-054). No SMTP/SES/etc. is chosen here; the
    invitation is fully functional without it because the plaintext token
    is returned once at creation for manual delivery.

    Promoting this to a real provider later changes zero call sites:
    `AdministrationService.create_invitation` already calls
    `notify_invitation_created` at the position a real send would occupy.
    Never logs the plaintext token itself.
    """

    def notify_invitation_created(
        self, invitation: Invitation, plaintext_token: str
    ) -> None:
        logger.info(
            "invitation notification (no-op): would deliver invitation id=%s "
            "to email=%s org=%s",
            invitation.id,
            invitation.email,
            invitation.organization_id,
        )
