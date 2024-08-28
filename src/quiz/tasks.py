from datetime import timedelta
import json
import time

from celery import shared_task
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from core.utils import memcache_lock
from quiz.constants import (
    ANSWER_TIME_SECOND,
    REST_BETWEEN_EACH_QUESTION_SECOND,
)
from quiz.models import Competition, Question, UserCompetition
from quiz.serializers import QuestionSerializer
import logging
import math

from quiz.utils import get_quiz_question_state, is_competition_finsihed

logger = logging.getLogger(__name__)


def handle_quiz_end(competition: Competition):
    pass


def evaluate_state(competition: Competition, channel_layer):
    question_state = get_quiz_question_state(competition)

    logger.warning(f"sending broadcast question {question_state}.")

    if is_competition_finsihed(competition):
        handle_quiz_end(competition)
        logger.warning(f"no more questions remaining, broadcast quiz finished.")

        logger.info("calculating results")
        question_number = get_quiz_question_state(competition)

        users_participated = UserCompetition.objects.filter(
            competition=competition
        )

        winners = users_participated.annotate(
            correct_answer_count=Count('users_answer', filter=Q(users_answer__selected_choice__is_correct=True))
        ).filter(
            correct_answer_count__gte=question_number
        )

        winners_count = winners.count()

        amount_win = competition.prize_amount

        winners.update(
            is_winner=True,
            amount_won=amount_win / winners_count if winners_count > 0 else 0
        )

        async_to_sync(channel_layer.group_send)(  # type: ignore
            f"quiz_{competition.pk}",
            {"type": "finish_quiz", "data": {  }},
        )
        return -1

    question = Question.objects.get(competition=competition, number=question_state)

    data = QuestionSerializer(instance=question).data

    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_{competition.pk}",
        {"type": "send_question", "data": json.dumps(data, cls=DjangoJSONEncoder)},
    )

    start_time = time.monotonic()  # Record the start time

    time.sleep(ANSWER_TIME_SECOND)

    elapsed_time = time.monotonic() - start_time  # Calculate the elapsed time

    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_{competition.pk}",
        {"type": "send_quiz_stats", "data": ""},
    )

    # Adjust rest time by subtracting the elapsed time from it
    rest_time = max(0, REST_BETWEEN_EACH_QUESTION_SECOND - elapsed_time)

    return rest_time


@shared_task(bind=True)
def setup_competition_to_start(self, competition_pk):
    channel_layer = get_channel_layer()

    try:
        competition: Competition = Competition.objects.get(pk=competition_pk)
    except Competition.DoesNotExist:
        logger.warning(f"Competition with pk {competition_pk} not exists.")
        return

    state = "IDLE"

    rest_still = (competition.start_at - timezone.now()).total_seconds()
    logger.warning(f"Resting {rest_still} seconds till the quiz begins and broadcast the questions.")

    while state != "FINISHED" or rest_still > 0:
        time.sleep(rest_still)

        start_time = time.monotonic()  # Record the start time before evaluating the state
        rest_still = evaluate_state(competition, channel_layer)
        elapsed_time = time.monotonic() - start_time  # Calculate the elapsed time

        if rest_still == -1:
            state = "FINISHED"
            break

        # Adjust the rest time by subtracting the elapsed time from it
        rest_still = max(0, rest_still - elapsed_time)

    time.sleep(2)
    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_{competition.pk}",
        {"type": "send_quiz_stats", "data": None},
    )
