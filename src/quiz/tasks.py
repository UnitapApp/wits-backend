import json
import time

from celery import shared_task
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from quiz.constants import (
    ANSWER_TIME_SECOND,
    REST_BETWEEN_EACH_QUESTION_SECOND,
)
from quiz.contracts import ContractManager, SafeContractException
from quiz.models import Competition, Question, UserCompetition
from quiz.serializers import QuestionSerializer
import logging
import math

from quiz.utils import get_quiz_question_state, is_competition_finsihed

logger = logging.getLogger(__name__)

@shared_task()
def handle_quiz_end(competition: Competition, winners: list[str], amount):
    manager = ContractManager()

    win_amount = int(amount)

    try:
        tx = manager.distribute(winners, [win_amount for i in winners])
    except SafeContractException as e:
        handle_quiz_end.delay(competition, winners, amount)
        raise e
    
    competition.tx_hash = str(tx.hex())

    competition.save()

    logger.info("tx hash for winners distribution", tx)

    return tx


def check_competition_state(competition: Competition):
    pass


def evaluate_state(competition: Competition, channel_layer, question_state):

    logger.warning(f"sending broadcast question {question_state}.")

    if competition.questions.count() < question_state:
        logger.warning(f"no more questions remaining, broadcast quiz finished.")

        logger.info("calculating results")
        question_number = get_quiz_question_state(competition)

        users_participated = UserCompetition.objects.filter(
            competition=competition
        )

        winners = users_participated.annotate(
            correct_answer_count=Count('users_answer', filter=Q(users_answer__selected_choice__is_correct=True))
        ).filter(
            correct_answer_count__gte=question_number,
            competition=competition
        ).distinct()

        winners_count = winners.count()

        amount_win = competition.prize_amount

        win_amount = amount_win / winners_count if winners_count > 0 else 0

        winners.update(
            is_winner=True,
            amount_won=win_amount
        )
        
        if win_amount:
            handle_quiz_end(competition, list(winners.values_list("user_profile__wallet_address", flat=True)), win_amount)

        else:
            competition.tx_hash = "0x00"
            competition.save()


        channel_layer = get_channel_layer()
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

    try:
        competition: Competition = Competition.objects.get(pk=competition_pk)
    except Competition.DoesNotExist:
        logger.warning(f"Competition with pk {competition_pk} not exists.")
        return

    state = "IDLE"

    rest_still = (competition.start_at - timezone.now()).total_seconds() - 1
    question_index = 1
    logger.warning(f"Resting {rest_still} seconds till the quiz begins and broadcast the questions.")

    while state != "FINISHED" or rest_still > 0:
        time.sleep(rest_still)
        rest_still = evaluate_state(competition, channel_layer, question_index)
        question_index += 1
        if rest_still == -1:
            state = "FINISHED"
            break

    time.sleep(2)
    async_to_sync(channel_layer.group_send)(  # type: ignore
        f"quiz_{competition.pk}",
        {"type": "send_quiz_stats", "data": None},
    )
