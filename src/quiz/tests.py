from django.utils import timezone
from django.urls import reverse

from authentication.models import UserProfile
from quiz.models import Choice, Competition, Question
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from quiz.constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND
from quiz.utils import get_quiz_question_state, is_competition_finsihed

User = get_user_model()


CORRECT_CHOICE_INDEX = 3
HINT_CHOICES = [0, 2]
PRIZE_AMOUNT = 20000


class QuizRestfulTestCase(APITestCase):
    questions_list: list[Question] = []

    correct_choice_index = CORRECT_CHOICE_INDEX
    hint_choices = HINT_CHOICES

    competition: Competition

    user_profile: UserProfile

    token: str

    def enroll_user(self, user: UserProfile, competition: Competition):
        pass

    def create_test_user(self):
        user = User.objects.create_user("test_user")
        profile = UserProfile.objects.create(
            user=user, wallet_address="0x623123123", username="test_user"
        )

        self.user_profile = profile

        self.token = Token.objects.get_or_create(user=user)[0].key

    def create_sample_question(self, question_number: int):
        question = Question.objects.create(
            competition=self.competition,
            text=f"Sample question number {question_number}",
            number=question_number,
        )

        for i in range(4):
            is_choice_correct = i == self.correct_choice_index

            choice = Choice.objects.create(
                question=question,
                is_correct=is_choice_correct,
                text=f"Sample Answer [{i}]",
                is_hinted_choice=bool(i in self.hint_choices),
            )

        return question

    def reverse_url(self, path, *args, **kwargs):
        return reverse(f"{self.app_name}:{path}", args=args, kwargs=kwargs)

    def setUp(self):
        self.app_name = "QUIZ"
        self.create_test_user()
        self.competition = Competition.objects.create(
            title="Test Competition",
            start_at=timezone.now() - timezone.timedelta(minutes=5),
            user_profile=self.user_profile,
            prize_amount=PRIZE_AMOUNT,
            chain_id=10,
            token_decimals=6,
            token="USDC",
            token_address="0x",
            email_url="test@test.test",
        )

        self.questions_list = [
            self.create_sample_question(1),
            self.create_sample_question(2),
            self.create_sample_question(3),
            self.create_sample_question(4),
        ]

    def update_quiz_start_at(self, start_at):
        self.competition.start_at = start_at
        self.competition.save(update_fields=["start_at"])

    def get_authenticated_headers(self):
        return {"Authorization": f"TOKEN {self.token}"}

    def test_competition_status(self):
        self.assertFalse(
            self.competition.is_in_progress, "Competition is not in progress"
        )
        self.assertTrue(self.competition.can_be_shown, "Competition can be shown")
        self.assertTrue(
            is_competition_finsihed(self.competition), "Competition is finished"
        )

    def test_user_enroll(self):
        res = self.client.get(self.reverse_url("competition-list"))

        self.assertEqual(res.status_code, 200)

        data = res.json()

        self.assertEqual(data["count"], 1, "Only 1 competition")
        self.assertEqual(
            data["results"][0]["id"],
            self.competition.pk,
            "competition Primary keys matches",
        )
        self.assertEqual(
            data["results"][0]["participantsCount"],
            0,
            "No participants on recently created competition",
        )
        self.assertEqual(
            data["results"][0]["prizeAmount"],
            float(self.competition.prize_amount),
            "Prizes on competition must match",
        )

        enroll_res = self.client.post(
            self.reverse_url("enroll-competition"),
            data={"competition": self.competition.pk},
            headers=self.get_authenticated_headers(),
        )

        self.assertEqual(
            enroll_res.status_code, 400, "Not Allowed to enroll when quiz is finished"
        )

        self.update_quiz_start_at(timezone.now() + timezone.timedelta(minutes=5))

        enroll_res = self.client.post(
            self.reverse_url("enroll-competition"),
            data={"competition": self.competition.pk},
            headers=self.get_authenticated_headers(),
        )

        self.assertEqual(
            enroll_res.status_code, 201, "Allow to enroll when the quiz is not started"
        )

        res = self.client.get(self.reverse_url("competition-list"))
        data = res.json()
        self.assertEqual(
            data["results"][0]["participantsCount"],
            1,
            "Added user to the participants count",
        )

        self.competition.is_active = False

        self.competition.save(update_fields=["is_active"])
        res = self.client.get(self.reverse_url("competition-list"))
        data = res.json()
        self.assertEqual(data["count"], 0, "Remove the quiz if is_active is False")

    def test_questions_state(self):

        self.assertEqual(
            get_quiz_question_state(self.competition),
            self.competition.questions.count(),
            "The quiz is finished so we are in the last question state",
        )

        self.update_quiz_start_at(
            timezone.now() - timezone.timedelta(seconds=ANSWER_TIME_SECOND - 2)
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 1, "We are in question 1"
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND - 0.5
            )
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 1, "We are in question 1"
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND + REST_BETWEEN_EACH_QUESTION_SECOND
            )
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 2, "We are in question 2"
        )

        self.update_quiz_start_at(
            timezone.now()
            - timezone.timedelta(
                seconds=ANSWER_TIME_SECOND * 2 + REST_BETWEEN_EACH_QUESTION_SECOND
            )
        )

        self.assertEqual(
            get_quiz_question_state(self.competition), 2, "We are in question 2"
        )
