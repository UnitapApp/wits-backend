from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import F
from .constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND




class Sponsor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    link = models.URLField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = CloudflareImagesField(blank=True, null=True, variant="public")



class CompetitionManager(models.Manager):
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


class Competition(models.Model):
    title = models.CharField(max_length=255)
    sponsor = models.ManyToManyField(
        Sponsor,
        related_name="competitions",
        blank=True,
    )
    user_profile = models.PositiveBigIntegerField()
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_at = models.DateTimeField(null=False, blank=False)
    prize_amount = BigNumField(null=False, blank=False)
    chain = models.ForeignKey(
        Chain,
        blank=False,
        null=False,
        on_delete=models.PROTECT,
        related_name="competitions",
    )
    token = models.CharField(max_length=100)
    token_address = models.CharField(max_length=255)
    discord_url = models.URLField(max_length=255, null=True, blank=True)
    twitter_url = models.URLField(max_length=255, null=True, blank=True)
    email_url = models.EmailField(max_length=255)
    telegram_url = models.URLField(max_length=255, null=True, blank=True)
    image_url = models.URLField(max_length=255, null=True, blank=True)
    token_image_url = models.URLField(max_length=255, null=True, blank=True)

    participants = models.ManyToManyField(
        UserProfile, through="UserCompetition", related_name="participated_competitions"
    )
    winner_count = models.IntegerField(default=0)
    amount_won = BigNumField(default=0)

    is_active = models.BooleanField(default=True)

    objects: CompetitionManager = CompetitionManager()

    def __str__(self):
        return f"{self.user_profile.username} - {self.title}"

    def can_be_shown(self):
        return self.start_at >= timezone.now()

class UserCompetition(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    is_winner = models.BooleanField(default=False)
    amount_won = BigNumField(default=0)

    class Meta:
        unique_together = ("user_profile", "competition")

    def __str__(self):
        return f"{self.user_profile.username} - {self.competition.title}"



class QuestionManager(models.Manager):
    @property
    def can_be_shown(self):
        return self.filter(competition__start_at__gte=timezone.now())


class Question(models.Model):
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

    class Meta:
        unique_together = ("competition", "number")


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    is_hinted_choice = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class UserAnswer(models.Model):
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
            f"{self.user_competition.user_profile.username} "
            f"- {self.user_competition.competition.title}  - {self.question.number}"
        )
