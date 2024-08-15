from django.core.cache import cache
from django.utils import timezone

from authentication.models import ApiUserProfile
from quiz.models import Competition, UserCompetition


def is_user_eligible_to_participate(
    user_profile: ApiUserProfile, competition: Competition
) -> bool:
    try:
        user_competition = UserCompetition.objects.get(
            user_profile=user_profile, competition=competition
        )
    except UserCompetition.DoesNotExist:
        return False
    

    has_wrong_answer = user_competition.users_answer.filter(selected_choice__is_correct=False).exists()

    return (
        competition.is_active
        and competition.is_in_progress
        and (not has_wrong_answer)
    )
