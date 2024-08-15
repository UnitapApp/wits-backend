from rest_framework.permissions import BasePermission

from authentication.utils import resolve_user_from_request
from quiz.models import UserCompetition
from quiz.utils import is_user_eligible_to_participate


class IsEligibleToAnswer(BasePermission):
    """
    Permission to allow access if the
    user is eligible to answer questions in the competition.
    """

    def has_permission(self, request, view):
        user_competition_pk = request.data.get("user_competition")
        if user_competition_pk is None:
            return False

        user_profile = resolve_user_from_request(request)
        
        try:
            user_competition = UserCompetition.objects.get(pk=user_competition_pk)
            return is_user_eligible_to_participate(
                user_profile, user_competition.competition
            )
        except UserCompetition.DoesNotExist:
            return False
