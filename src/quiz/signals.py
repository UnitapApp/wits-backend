from celery import current_app
from django.utils import timezone
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from quiz.models import Competition
from quiz.tasks import setup_competition_to_start
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@receiver(pre_delete, sender=Competition)
def clean_competition_task(sender, instance: Competition, **kwargs):
    channel_layer = get_channel_layer()

    current_app.control.revoke(f"start_competition_{instance.pk}", terminate=True) # type: ignore

    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_list",
        {"type": "delete_competition", "data": instance.pk},
    )



@receiver(post_save, sender=Competition)
def trigger_competition_starter_task(sender, instance: Competition, created, **kwargs):
    
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_list",
        {"type": "update_competition_data", "data": instance.pk},
    )

    if not instance.is_active:
        return

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
