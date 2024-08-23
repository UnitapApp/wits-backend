import math
from django.core.cache import cache
from django.utils import timezone

from authentication.models import UserProfile
from quiz.constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND
from quiz.models import Competition, UserCompetition


def is_user_eligible_to_participate(
    user_profile: UserProfile | None, competition: Competition
) -> bool:
    if not user_profile:
        return False
    try:
        user_competition = UserCompetition.objects.get(
            user_profile=user_profile, competition=competition
        )
    except UserCompetition.DoesNotExist:
        return False

    has_wrong_answer = user_competition.users_answer.filter(
        selected_choice__is_correct=False
    ).exists()

    if (
        competition.is_active
        and competition.is_in_progress
        and (not has_wrong_answer) is False
    ):
        return False

    question_number = user_competition.users_answer.count()

    state = math.floor(
        (timezone.now() - competition.start_at).seconds
        / (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
    )

    if state + 1 > question_number:
        return False

    return True
