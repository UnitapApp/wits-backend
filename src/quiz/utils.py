import math
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

    state = get_quiz_question_state(competition) - 1

    if state > question_number:
        return False

    return True



def get_quiz_question_state(competition: Competition):
 
    start_at = competition.start_at

    if timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
    else:
        start_at = start_at.astimezone(timezone.get_current_timezone())

    if start_at > timezone.now():
        return 0
    
    return min(math.floor(
        (timezone.now() - start_at).seconds
        / (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
    ) + 1, competition.questions.count())


def is_competition_finsihed(competition: Competition):
    start_at = competition.start_at

    if timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
    else:
        start_at = start_at.astimezone(timezone.get_current_timezone())

    if start_at > timezone.now():
        return False
    
    return math.floor(
        (timezone.now() - start_at).seconds
        / (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)
    ) + 1 > competition.questions.count()
    