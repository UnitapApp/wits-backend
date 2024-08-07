from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import F

from lib.models import BaseModel
from .constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND



class CompetitionManager(BaseModel):
    @property
    def not_started(self):
        return self.filter(start_at__lt=timezone.now())
    
    @property
    def finished(self):
        return self.filter(
            start_at__gt=timezone.now() - timezone.timedelta(seconds=F("questions"))
        )
    
    @property
    def started(self):
        return self.filter(start_at__gte=timezone.now())
    
    @property
    def in_progress(self):
        return self.filter(
            start_at__lte=timezone.now() - timezone.timedelta(seconds=F("questions"))
        ).filter(
            start_at__gt=timezone.now()
        )


class Competition(BaseModel):
    title = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_at = models.DateTimeField(null=False, blank=False)
    prize_amount = models.PositiveBigIntegerField(null=False, blank=False)
    token = models.CharField(max_length=100)
    token_address = models.CharField(max_length=255)
    discord_url = models.URLField(max_length=255, null=True, blank=True)
    twitter_url = models.URLField(max_length=255, null=True, blank=True)
    email_url = models.EmailField(max_length=255)
    telegram_url = models.URLField(max_length=255, null=True, blank=True)
    image_url = models.URLField(max_length=255, null=True, blank=True)
    token_image_url = models.URLField(max_length=255, null=True, blank=True)

    winner_count = models.IntegerField(default=0)
    amount_won = models.PositiveBigIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    objects: CompetitionManager = CompetitionManager()

    def __str__(self):
        return f"{self.title}"

    def can_be_shown(self):
        return self.start_at >= timezone.now()

class UserCompetition(BaseModel):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    is_winner = models.BooleanField(default=False)
    amount_won = models.PositiveBigIntegerField(default=0)


    def __str__(self):
        return self.competition.title



class QuestionManager(models.Manager):
    @property
    def can_be_shown(self):
        return self.filter(competition__start_at__gte=timezone.now())


class Question(BaseModel):
    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="questions"
    )
    number = models.IntegerField(
        null=False, blank=False, validators=[MinValueValidator(1)]
    )
    text = models.TextField()

    @property
    def can_be_shown(self):
        return self.competition.start_at + timezone.timedelta(seconds=(self.number - 1) * (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND)) <= timezone.now()
    
    @property
    def answer_can_be_shown(self):
        return self.competition.start_at + timezone.timedelta(seconds=(self.number - 1) * (ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND) + ANSWER_TIME_SECOND) <= timezone.now()

    objects: QuestionManager = QuestionManager()

    def __str__(self):
        return f"{self.competition.title} - {self.number} - {self.text}"

    class Meta(BaseModel.Meta):
        unique_together = ("competition", "number")


class Choice(BaseModel):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class UserAnswer(BaseModel):
    user_competition = models.ForeignKey(
        UserCompetition,
        on_delete=models.CASCADE,
        related_name="users_answer",
        null=False,
        blank=False,
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="users_answer",
        null=False,
        blank=False,
    )
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        related_name="users_answer",
        null=False,
        blank=False,
    )

    class Meta:
        unique_together = ("user_competition", "question")

    def __str__(self):
        return (
            f"{self.user_competition.competition.title}  - {self.question.number}"
        )
