import json
from typing import Any
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
)
from channels.db import database_sync_to_async
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from quiz.serializers import CompetitionSerializer, QuestionSerializer, UserAnswerSerializer
from quiz.utils import get_quiz_question_state, is_user_eligible_to_participate
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from .models import Competition, Question, Choice, UserCompetition, UserAnswer

import json
import logging


logger = logging.getLogger(__name__)


class QuizConsumer(AsyncJsonWebsocketConsumer):
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

        diff = get_quiz_question_state(self.competition) - answers.count()
        missed_answers = []

        if diff > 0:
            for i in range(diff):
                question = Question.objects.get(number=answers.count() + i + 1, competition=self.competition)
                answer = UserAnswer(
                    user_competition=UserCompetition.objects.get(user_profile=self.user_profile, competition=self.competition),
                    question=question,
                    id=-1
                )
                missed_answers.append(answer)

        serialized_answers = UserAnswerSerializer(list(answers) + missed_answers, many=True)

        return list(map(lambda x: x if x["selected_choice"] else { **x, "selected_choice": { "is_correct": False, "id": None } }, serialized_answers.data))

    @database_sync_to_async
    def resolve_user(self):
        return self.scope['user'].profile


    @classmethod
    async def encode_json(cls, content):
        return CamelCaseJSONRenderer().render(content).decode("utf-8")

    @database_sync_to_async
    def get_competition(self):
        return Competition.objects.get(pk=self.competition_id)

    async def send_question(self, event):
        question_data = event["data"]

        await self.send_json({"question": {**json.loads(question_data), "is_eligible": await database_sync_to_async(lambda:  is_user_eligible_to_participate(self.user_profile, self.competition))()}, "type": "new_question"})

    async def finish_quiz(self, event):
        question_data = event["data"]

        await self.send_json({"stats": question_data, "event": "quiz_finish"})

        await self.disconnect(0)

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
            "questions_count": self.competition.questions.count(),
        }

    async def get_current_question(self):
        competition_time = self.competition.start_at

        now = timezone.now()

        if now < competition_time:
            return {"error": "wait for competition to begin", "data": None}

        state = get_quiz_question_state(competition=self.competition) + 1

        question = await self.get_question(state)

        return {"question": question, "type": "new_question"}
    
    @database_sync_to_async
    def get_competition_stats(self) -> Any:
        return CompetitionSerializer(instance=self.competition).data

    async def connect(self):
        self.competition_id = self.scope["url_route"]["kwargs"]["competition_id"]

        self.competition_group_name = f"quiz_{self.competition_id}"
        self.competition: Competition = await self.get_competition()
        self.user_profile = await self.resolve_user()
        await self.accept()

        if not self.channel_layer:
            return

        await self.channel_layer.group_add(
            self.competition_group_name, self.channel_name
        )
        await self.send_json({ "type": "answers_history", "data": await self.send_user_answers() })

        if await database_sync_to_async(lambda: self.competition.is_in_progress)():
            await self.send_json(await self.get_current_question())

        else:
            await self.send_json(await self.get_competition_stats())

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

            if command == "ANSWER":
                if not await self.is_user_eligible_to_participate():
                    return

                res = await self.save_answer(
                    data["args"]["question_id"],
                    data["args"]["selected_choice_id"],
                )

                await self.send_json({ "type": "ANSWER_ADD", "data": {**res, "is_eligible": res["is_correct"], "competition": await self.get_competition_stats()} })

        except Exception as e:
            logger.warn(e)
        # if not self.channel_layer:
        #     return

        # await self.channel_layer.group_send(
        #     self.competition_group_name, {"type": "quiz_message", "message": data}
        # )

    async def quiz_message(self, event):
        message = event["message"]

        await self.send(text_data=json.dumps({"message": message}))

    @database_sync_to_async
    def save_answer(self, question_id, selected_choice_id):
        question = Question.objects.can_be_shown.get(pk=question_id)
        selected_choice = Choice.objects.get(pk=selected_choice_id)
        user_competition = UserCompetition.objects.get(
            user_profile=self.user_profile,
            competition_id=self.competition_id,
        )

        answer = UserAnswer.objects.create(
            user_competition=user_competition,
            question=question,
            selected_choice=selected_choice,
        )

        return {
            "type": "submit_answer_result",
            "answer": {
                "is_correct": selected_choice.is_correct,
                "answer": UserAnswerSerializer(instance=answer, context={ "create": True }).data,
            }
        }
