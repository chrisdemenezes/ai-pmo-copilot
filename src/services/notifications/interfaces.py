from typing import Protocol

from src.database.models import Invitation


class NotificationProvider(Protocol):
    """Delivery seam for outbound notifications (item 6, Convites -- D-054).

    The Invitation domain is complete without any concrete provider: the
    plaintext token is returned once at creation for manual delivery. This
    Protocol is where a future SMTP/SES/etc. provider plugs in to deliver
    the invitation automatically -- a business decision (communication
    model) that stays pending without blocking the domain. Same discipline
    as `EventEmitter`/`NoOpEventEmitter` (Event Foundation, D-049): the seam
    exists, the concrete provider doesn't yet.
    """

    def notify_invitation_created(
        self, invitation: Invitation, plaintext_token: str
    ) -> None: ...
