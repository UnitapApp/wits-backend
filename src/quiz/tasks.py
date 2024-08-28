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

from quiz.utils import get_quiz_question_state

logger = logging.getLogger(__name__)


def handle_quiz_end(competition: Competition):
    pass


def evaluate_state(competition: Competition, channel_layer):

    question_state = get_quiz_question_state(competition)

    logger.warning(f"sending broadcast question {question_state}.")

    if question_state > competition.questions.count():
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

    time.sleep(ANSWER_TIME_SECOND)

    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_{competition.pk}",
        {"type": "send_quiz_stats", "data": ""},
    )

    return REST_BETWEEN_EACH_QUESTION_SECOND


@shared_task(bind=True)
def setup_competition_to_start(self, competition_pk):
    channel_layer = get_channel_layer()

    # id_ = f"QUIZ-{competition_pk}-LOCK"

    # acquired = memcache_lock(id_, self.app.oid)

    # if not acquired:
    #     logging.warning(f"Could not acquire process lock at {self.name}")
    #     return

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
        rest_still = evaluate_state(competition, channel_layer)

        if rest_still == -1:
            state = "FINISHED"
            break

    time.sleep(2)
    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_{competition.pk}",
        {"type": "send_quiz_stats", "data": None},
    )

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
