from celery import current_app
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from quiz.models import Competition
from quiz.tasks import setup_competition_to_start


@receiver(post_save, sender=Competition)
def trigger_competition_starter_task(sender, instance: Competition, created, **kwargs):

    start_time = instance.start_at

    if start_time < timezone.now():
        return

    # This assumes the task is scheduled with a unique name using the competition ID.
    # current_app.control.revoke(f"start_competition_{instance.pk}", terminate=True)

    setup_competition_to_start.apply_async(
        args=[instance.pk],
        eta=start_time - timezone.timedelta(seconds=10),
        task_id=f"start_competition_{instance.pk}",
    ) # type: ignore
