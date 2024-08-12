from django.core.cache import cache
from django.utils import timezone

from quiztap.models import Competition, UserCompetition


def is_user_eligible_to_participate(
    user_profile, competition: Competition
) -> bool:
    return True