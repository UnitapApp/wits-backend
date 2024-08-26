from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from django.utils import timezone

from quiz.paginations import StandardResultsSetPagination
from quiz.filters import CompetitionFilter, NestedCompetitionFilter
from quiz.models import Competition, Question, UserAnswer, UserCompetition
from quiz.permissions import IsEligibleToAnswer
from quiz.serializers import (
    CompetitionSerializer,
    QuestionSerializer,
    UserAnswerSerializer,
    UserCompetitionSerializer,
)


class CompetitionViewList(ListAPIView):
    filter_backends = []
    queryset = Competition.objects.filter(is_active=True).order_by("-created_at")
    pagination_class = StandardResultsSetPagination
    serializer_class = CompetitionSerializer


class CompetitionView(RetrieveAPIView):
    queryset = Competition.objects.filter(is_active=True)
    serializer_class = CompetitionSerializer


class QuestionView(RetrieveAPIView):
    http_method_names = ["get"]
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()


class EnrollInCompetitionView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [CompetitionFilter]
    queryset = UserCompetition.objects.all()
    serializer_class = UserCompetitionSerializer

    def perform_create(self, serializer):
        user = self.request.user.profile # type: ignore
        serializer.save(user_profile=user)

    def get_queryset(self):
        return self.queryset.filter(user_profile=self.request.user.profile) # type:ignore


class UserAnswerView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsEligibleToAnswer]
    serializer_class = UserAnswerSerializer
    filter_backends = [NestedCompetitionFilter]
    queryset = UserAnswer.objects.all()


    def get_queryset(self):
        return self.queryset.filter(
            competition__start_at__gte=timezone.now()
        )

    def perform_create(self, serializer):
        serializer.save()
