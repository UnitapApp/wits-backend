import json
import math
from typing import Any
from channels.generic.websocket import (
    AsyncWebsocketConsumer,
    AsyncJsonWebsocketConsumer,
)
from channels.db import database_sync_to_async
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from authentication.utils import resolve_user_from_token
from quiz.constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND
from quiz.serializers import CompetitionSerializer, QuestionSerializer
from quiz.utils import is_user_eligible_to_participate

from .models import Competition, Question, Choice, UserCompetition, UserAnswer

import json


class QuizConsumer(AsyncJsonWebsocketConsumer):
    @database_sync_to_async
    def get_competition(self):
        return Competition.objects.select_related("questions").get(
            pk=self.competition_id
        )

    async def send_question(self, event):
        question_data = event["data"]

        await self.send(
            text_data=json.dumps({"question": question_data, "type": "new_question"})
        )

    @database_sync_to_async
    def get_question(self, index: int):
        instance = Question.objects.can_be_shown.filter(
            competition__pk=self.competition_id, number=index
        ).first()

        return QuestionSerializer(instance=instance).data

    @database_sync_to_async
    def is_user_eligible_to_participate(self):
        return is_user_eligible_to_participate(
            user_profile=self.user_profile, competition=self.competition
        )

    @database_sync_to_async
    def get_quiz_stats(self):
        prize_to_win = self.competition.prize_amount
        users_participated = UserCompetition.objects.filter(
            competition=self.competition
        )
        users_participating = users_participated.count()

        return {
            "users_participating": users_participating,
            "prize_to_win": prize_to_win / users_participating,
            "total_participants_count": self.competition.participants.count(),
        }

    async def get_current_question(self):
        competition_time = self.competition.start_at

        now = timezone.now()

        if now < competition_time:
            return {"error": "wait for competition to begin", "data": None}

        time_passed = now - competition_time

        state = (
            math.floor(
                time_passed.seconds
                / (REST_BETWEEN_EACH_QUESTION_SECOND + ANSWER_TIME_SECOND)
            )
            + 1
        )
        question = await self.get_question(state)

        return {"error": "", "data": {"state": state, "question": question}}

    def get_competition_stats(self) -> Any:
        return CompetitionSerializer(instance=self.competition).data

    async def connect(self):
        self.competition_id = self.scope["url_route"]["kwargs"]["competition_id"]
        self.competition_group_name = f"quiz_{self.competition_id}"
        self.competition: Competition = await self.get_competition()

        if not self.channel_layer:
            return

        await self.channel_layer.group_add(
            self.competition_group_name, self.channel_name
        )

        await self.accept()

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

        if command == "GET_COMPETITION":
            await self.send_json(self.get_competition_stats())

        if command == "GET_STATS":
            await self.send_json(self.get_quiz_stats())

        if command == "GET_QUESTION":
            await self.send_json(await self.get_question(data["args"]["index"]))

        if command == "ANSWER":
            if not await self.is_user_eligible_to_participate():
                return

            res = await self.save_answer(
                data["args"]["question_id"],
                data["args"]["selected_choice_id"],
                data["args"]["token"],
            )

            await self.send_json({**res, "is_eligible": res["is_correct"]})

        if not self.channel_layer:
            return

        await self.channel_layer.group_send(
            self.competition_group_name, {"type": "quiz_message", "message": data}
        )

    async def quiz_message(self, event):
        message = event["message"]

        await self.send(text_data=json.dumps({"message": message}))

    @database_sync_to_async
    def save_answer(self, question_id, selected_choice_id, token):
        question = Question.objects.can_be_shown.get(pk=question_id)
        selected_choice = Choice.objects.get(pk=selected_choice_id)
        user_competition = UserCompetition.objects.get(
            user_profile=resolve_user_from_token(token),
            competition_id=self.competition_id,
        )

        UserAnswer.objects.create(
            user_competition=user_competition,
            question=question,
            selected_choice=selected_choice,
        )

        return {
            "is_correct": selected_choice.is_correct,
            "competition": self.get_competition_stats(),
        }
