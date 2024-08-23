import json
import time

from celery import shared_task
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from core.utils import memcache_lock
from quiz.constants import (
    ANSWER_TIME_SECOND,
    REGISTER_COMPETITION_TASK_PERIOD_SECONDS,
    REST_BETWEEN_EACH_QUESTION_SECOND,
)
from quiz.models import Competition, Question, UserCompetition
from quiz.serializers import QuestionSerializer
import logging
import math



logger = logging.getLogger(__name__)


def handle_quiz_end(competition: Competition):
    pass


def evaluate_state(competition: Competition, channel_layer):
    time_scale = timezone.now() - competition.start_at

    question_state = (
        math.floor(
            time_scale.seconds
            / (REST_BETWEEN_EACH_QUESTION_SECOND + ANSWER_TIME_SECOND)
        )
        + 1
    )
    logger.warning(f"sending broadcast question {question_state}.")

    if question_state - 1 > competition.questions.count():
        handle_quiz_end(competition)
        logger.warning(f"no more questions remaining, broadcast quiz finished.")
        async_to_sync(channel_layer.group_send)(  # type: ignore
            f"quiz_{competition.pk}",
            {"type": "finish_quiz", "data": {  }},
        )
        return -1

    question = Question.objects.get(competition=competition, number=question_state)

    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_{competition.pk}",
        {"type": "send_question", "data": json.dumps(QuestionSerializer(instance=question).data, cls=DjangoJSONEncoder)},
    )

    # calculate the amount to be sleep
    return ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND


@shared_task()
def setup_competition_to_start(competition_pk):
    channel_layer = get_channel_layer()

    try:
        competition = Competition.objects.get(pk=competition_pk)
    except Competition.DoesNotExist:
        logger.warning(f"Competition with pk {competition_pk} not exists.")
        return

    state = "IDLE"

    rest_still = (competition.start_at - timezone.now()).seconds
    logger.warning(f"Resting {rest_still} seconds till the quiz begins and broadcast the questions.")

    while state != "FINISHED":
        time.sleep(rest_still)
        rest_still = evaluate_state(competition, channel_layer)

        if rest_still == -1:
            state = "FINISHED"
            break

    # question = competition.questions.order_by("number").first()

    # if not question:
    #     logging.warning(f"No questions found for competition {competition_pk}.")
    #     return


    # async_to_sync(channel_layer.group_send)(  # type: ignore
    #     f"quiz_{competition_pk}",
    #     {"type": "send_question", "data": QuestionSerializer(instance=question).data},
    # )

    # user_competition_count = competition.participants.count()
    # cache.set(
    #     f"comp_{competition_pk}_total_participants_count", user_competition_count, 360
    # )


# @shared_task()
# def process_competition_questions(competition_pk, ques_pk):
#     try:
#         competition = Competition.objects.get(
#             pk=competition_pk, status=Competition.Status.IN_PROGRESS
#         )
#         question = Question.objects.get(pk=ques_pk)
#     except Competition.DoesNotExist:
#         logging.warning(f"Competition with pk {competition_pk} not exists.")
#         return
#     except Question.DoesNotExist:
#         logging.warning(f"Question with pk {ques_pk} not exists.")
#         return
#     question.can_be_shown = True
#     question.save(update_fields=("can_be_shown",))
#     process_competition_answers.apply_async(
#         (competition_pk, ques_pk),
#         eta=competition.start_at
#         + timedelta(
#             seconds=(
#                 (question.number * ANSWER_TIME_SECOND)
#                 + (question.number - 1) * REST_BETWEEN_EACH_QUESTION_SECOND
#             )
#         ),
#     )


# @shared_task()
# def process_competition_answers(competition_pk, ques_pk):
#     try:
#         competition = Competition.objects.get(pk=competition_pk)
#         current_question = Question.objects.prefetch_related("users_answer").get(
#             pk=ques_pk
#         )
#     except Competition.DoesNotExist:
#         logging.warning(f"Competition with pk {competition_pk} not exists.")
#         return
#     except Question.DoesNotExist:
#         logging.warning(f"Question with pk {ques_pk} not exists.")
#         return

#     current_question.answer_can_be_shown = True
#     current_question.save(update_fields=("answer_can_be_shown",))
#     next_question = (
#         competition.questions.filter(number__gt=current_question.number)
#         .order_by("number")
#         .first()
#     )
#     users_answered_correct = current_question.users_answer.filter(
#         selected_choice__is_correct=True
#     ).values_list("user_competition__pk", flat=True)

#     if next_question is None:
#         try:
#             amount_won = Decimal(competition.prize_amount / len(users_answered_correct))
#         except ZeroDivisionError:
#             logging.warning("no correct answer be found")
#         else:
#             UserCompetition.objects.filter(pk__in=users_answered_correct).update(
#                 is_winner=True, amount_won=amount_won
#             )
#             competition.amount_won = amount_won

#         competition.winner_count = len(users_answered_correct)
#         competition.status = competition.Status.FINISHED
#         competition.save(update_fields=("status", "amount_won", "winner_count"))
#         cache.delete(f"comp_{competition_pk}_eligible_users_count")
#         cache.delete(f"comp_{competition_pk}_eligible_users")
#         cache.delete(f"comp_{competition_pk}_total_participants_count")
#         return
#     user_competition_count = competition.participants.count()
#     cache.set(
#         f"comp_{competition_pk}_total_participants_count", user_competition_count, 360
#     )
#     cache.set(
#         f"comp_{competition_pk}_eligible_users_count", len(users_answered_correct), 360
#     )
#     cache.set(f"comp_{competition_pk}_eligible_users", set(users_answered_correct), 360)
#     process_competition_questions.apply_async(
#         (competition_pk, next_question.pk),
#         eta=competition.start_at
#         + timedelta(
#             seconds=(
#                 ((next_question.number - 1) * ANSWER_TIME_SECOND)
#                 + (next_question.number - 1) * REST_BETWEEN_EACH_QUESTION_SECOND
#             )
#         ),
#     )


# @shared_task(bind=True)
# def register_competition_to_start(self):
#     now = timezone.now()
#     id_ = f"{self.name}-LOCK"

#     with memcache_lock(id_, self.app.oid) as acquired:
#         if not acquired:
#             logging.warning(f"Could not acquire process lock at {self.name}")
#             return
#         threshold = now + timedelta(seconds=REGISTER_COMPETITION_TASK_PERIOD_SECONDS)

#         competitions = Competition.objects.filter(
#             start_at__lt=threshold,
#             is_active=True,
#             status=Competition.Status.NOT_STARTED,
#         )

#         for competition in competitions:
#             setup_competition_to_start.apply_async(
#                 (competition.pk,),
#                 eta=competition.start_at - timedelta(milliseconds=0.5),
#             )