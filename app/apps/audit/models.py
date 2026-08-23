from django.conf import settings
from django.db import models


class AuditEvent(models.Model):

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    action = models.CharField(
        max_length=100
    )

    target = models.CharField(
        max_length=255,
        blank=True,
    )

    details = models.JSONField(
        default=dict,
        blank=True,
    )

    success = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.created_at} "
            f"{self.action} "
            f"{self.target}"
        )

