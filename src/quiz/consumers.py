import json
from typing import Any
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
)
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Q, Count
from authentication.models import UserProfile
from quiz.serializers import CompetitionSerializer, QuestionSerializer, UserAnswerSerializer
from quiz.utils import get_quiz_question_state, is_user_eligible_to_participate
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from .models import Competition, Question, Choice, UserCompetition, UserAnswer

import json
import logging


logger = logging.getLogger(__name__)


class QuizConsumer(AsyncJsonWebsocketConsumer):
    user_competition: UserCompetition
    user_profile: UserProfile

    async def send_json(self, content, close=False):
        """
        Encode the given content as JSON and send it to the client.
        """
        await super().send(text_data=await self.encode_json(content), close=close)

    @database_sync_to_async
    def send_user_answers(self):
        if not self.user_profile:
            return {}
        
        answers = UserAnswer.objects.filter(user_competition__competition=self.competition, user_competition__user_profile=self.user_profile)

        diff = get_quiz_question_state(self.competition) - 1 - answers.count()
        missed_answers = []

        if diff > 0:
            for i in range(diff):
                question = Question.objects.get(number=answers.count() + i + 1, competition=self.competition)
                answer = UserAnswer(
                    user_competition=self.user_competition,
                    question=question,
                    id=-1
                )
                missed_answers.append(answer)

        serialized_answers = UserAnswerSerializer(list(answers) + missed_answers, many=True)

        return list(map(lambda x: x if x["selected_choice"] else { **x, "selected_choice": { "is_correct": False, "id": None } }, serialized_answers.data))

    @database_sync_to_async
    def resolve_user(self):
        return self.scope['user'].profile

    @database_sync_to_async
    def resolve_user_competition(self):
        return UserCompetition.objects.get(user_profile=self.user_profile, competition=self.competition)
    
    @database_sync_to_async
    def send_hint_question(self, question_id):
        
        user_competition = self.user_competition
        
        if not user_competition or user_competition.hint_count <= 0:
            return
        
        question: Question = Question.objects.get(pk=question_id, competition=self.competition)

        user_competition.hint_count -= 1
        user_competition.save()

        return list(question.choices.filter(is_hinted_choice=True).values_list('pk', flat=True))

    @classmethod
    async def encode_json(cls, content):
        return CamelCaseJSONRenderer().render(content).decode("utf-8")

    @database_sync_to_async
    def get_competition(self):
        return Competition.objects.filter(pk=self.competition_id).first()

    async def send_question(self, event):
        question_data = event["data"]

        await self.send_json({"question": {**json.loads(question_data), "is_eligible": await database_sync_to_async(lambda:  is_user_eligible_to_participate(self.user_profile, self.competition))()}, "type": "new_question"})

    async def send_quiz_stats(self, event):
        await self.send_json(await self.get_quiz_stats())

    @database_sync_to_async
    def calculate_quiz_winners(self):
        return list(UserCompetition.objects.filter(is_winner=True).values("user_profile__wallet_address", "tx_hash"))

    async def finish_quiz(self, event):

        winners = await self.calculate_quiz_winners()

        await self.send_json({"winners_list": winners, "type": "quiz_finish"})

    @database_sync_to_async
    def get_question(self, index: int):
        instance = Question.objects.can_be_shown.filter(
            competition__pk=self.competition_id, number=index
        ).first()

        data: Any = QuestionSerializer(instance=instance).data

        return {"question": {**data, "is_eligible": is_user_eligible_to_participate(self.user_profile, self.competition)}, "type": "new_question"}

    @database_sync_to_async
    def is_user_eligible_to_participate(self):
        return is_user_eligible_to_participate(
            user_profile=self.user_profile, competition=self.competition
        )
    
    def get_round_participants(self, total_participants, question_number):
        if question_number <= 0:
            return 0
        
        if question_number > self.competition.questions.count():
            return 0
        
        return total_participants.annotate(
            correct_answer_count=Count('users_answer', filter=Q(users_answer__selected_choice__is_correct=True))
        ).filter(
            correct_answer_count__gte=question_number
        ).count()

    @database_sync_to_async
    def get_quiz_stats(self):
        prize_to_win = self.competition.prize_amount
        users_participated = UserCompetition.objects.filter(
            competition=self.competition
        )

        question_number = get_quiz_question_state(self.competition)

        if self.competition.can_be_shown:
            users_participating = users_participated.annotate(
                correct_answer_count=Count('users_answer', filter=Q(users_answer__selected_choice__is_correct=True))
            ).filter(
                correct_answer_count__gte=question_number
            )
        else:
            users_participating = users_participated

        participating_count = users_participating.count()

        return {
            "type": "quiz_stats",
            "data": {
                "users_participating": participating_count,
                "prize_to_win": prize_to_win / participating_count if participating_count > 0 else 0,
                "total_participants_count": self.competition.participants.count(),
                "questions_count": self.competition.questions.count(),
                "hint_count": self.user_competition.hint_count if self.user_competition else 0,
                "previous_round_losses": max(self.get_round_participants(users_participated, question_number - 1) - participating_count, 0)
            },
        }

    async def get_current_question(self):
        competition_time = self.competition.start_at

        now = timezone.now()

        if now < competition_time:
            return {"error": "wait for competition to begin", "data": None}

        state = (await database_sync_to_async(get_quiz_question_state)(competition=self.competition))

        question = await self.get_question(state)

        return question
    
    @database_sync_to_async
    def get_competition_stats(self) -> Any:
        return CompetitionSerializer(instance=self.competition).data

    async def connect(self):
        self.competition_id = self.scope["url_route"]["kwargs"]["competition_id"]

        self.competition_group_name = f"quiz_{self.competition_id}"
        self.competition: Competition = await self.get_competition()
        self.user_profile = await self.resolve_user()
        self.user_competition = await self.resolve_user_competition()

        await self.accept()

        if not self.channel_layer:
            return

        await self.channel_layer.group_add(
            self.competition_group_name, self.channel_name
        )
        await self.send_json({ "type": "answers_history", "data": await self.send_user_answers() })

        await self.send_json(await self.get_quiz_stats())

        if self.competition.start_at > timezone.now():
            await self.send_json({"type": "idle", "message": "wait for quiz to start"})

        elif await database_sync_to_async(lambda: self.competition.is_in_progress)():
            await self.send_json(await self.get_current_question())
        else:
            await self.finish_quiz(None)

    async def disconnect(self, close_code):
        await self.close()
        if not self.channel_layer:
            return

        await self.channel_layer.group_discard(
            self.competition_group_name, self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data["command"]

        if command == "PING":
            await self.send("PONG")

        if not self.user_profile:
            return

        try:
            if command == "GET_CURRENT_QUESTION":
                await self.send_json(await self.get_current_question())

            if command == "GET_COMPETITION":
                await self.send_json(await self.get_competition_stats())

            if command == "GET_STATS":
                await self.send_json(await self.get_quiz_stats())

            if command == "GET_QUESTION":
                await self.send_json(await self.get_question(data["args"]["index"]))

            if command == "GET_HINT":
                hint_choices = await self.send_hint_question(data['args']['question_id'])
                
                await self.send_json({ "type": "hint_question", "data": hint_choices, 'question_id': data['args']['question_id'] })

            if command == "ANSWER":
                is_eligible = await self.is_user_eligible_to_participate()

                if is_eligible is False:
                    return

                res = await self.save_answer( # TODO: parse parameters with django camel case
                    data["args"]["questionId"],
                    data["args"]["selectedChoiceId"],
                )

                await self.send_json({ "type": "add_answer", "data": {**res, "is_eligible": res["is_correct"], "question_id": data['args']['questionId']} })

        except Exception as e:
            logger.warn(e)

    async def quiz_message(self, event):
        message = event["message"]

        await self.send(text_data=json.dumps({"message": message}))

    @database_sync_to_async
    def save_answer(self, question_id, selected_choice_id):
        question: Question = Question.objects.can_be_shown.get(pk=question_id)
        selected_choice = Choice.objects.filter(pk=selected_choice_id).first()
        user_competition = self.user_competition

        answer = UserAnswer.objects.create(
            user_competition=user_competition,
            question=question,
            selected_choice_id=selected_choice_id,
        )

        if selected_choice and selected_choice.is_correct is True:
            correct_choice = selected_choice_id
        else:
            correct_choice = Choice.objects.filter(question=question, is_correct=True).first().pk

        return {
            "is_correct": selected_choice.is_correct if selected_choice else False,
            "answer": UserAnswerSerializer(instance=answer, context={ "create": True }).data,
            "question_number": question.number,
            "correct_choice": correct_choice
        }
