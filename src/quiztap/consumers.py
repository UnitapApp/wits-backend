import json
import math
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from quiztap.constants import ANSWER_TIME_SECOND, REST_BETWEEN_EACH_QUESTION_SECOND
from quiztap.serializers import CompetitionSerializer, QuestionSerializer

from .models import Competition, Question, Choice, UserCompetition, UserAnswer


class QuizConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def get_competition(self):
        return Competition.objects.select_related('questions').get(pk=self.competition_id)
    
    @database_sync_to_async
    def get_question(self, index: int):
        instance = Question.objects.can_be_shown.filter(
            competition__pk=self.competition_id,
            number=index
        ).first()

        return QuestionSerializer(instance=instance).data
    
    async def get_current_question(self):
        competition_time = self.competition.start_at

        now = timezone.now()

        if now < competition_time:
            return { "error": "wait for competition to begin", "data": None }
        
        time_passed = now - competition_time

        state = math.floor(time_passed.seconds / (REST_BETWEEN_EACH_QUESTION_SECOND + ANSWER_TIME_SECOND)) + 1
        question = await self.get_question(state)

        return { "error": "", "data": { "state": state, "question": question } }
        
    def get_competition_stats(self) -> dict:
        return CompetitionSerializer(instance=self.competition).data

    async def send_json(self, data):
        await self.send(json.dumps(data, cls=DjangoJSONEncoder))

    async def connect(self):
        self.competition_id = self.scope['url_route']['kwargs']['competition_id']
        self.competition_group_name = f'quiz_{self.competition_id}'
        self.competition: Competition = await self.get_competition()

        if not self.channel_layer: 
            return
        
        await self.channel_layer.group_add(
            self.competition_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if not self.channel_layer:
            return
        
        await self.channel_layer.group_discard(
            self.competition_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data['command']

        if command == "PING":
            await self.send("PONG")

        if command == "GET_COMPETITION":
            await self.send_json(self.get_competition_stats())

        if command == "GET_QUESTION":
            await self.send_json(await self.get_question(data['args']['index']))

        if not self.channel_layer:
            return
        
        await self.channel_layer.group_send(
            self.competition_group_name,
            {
                'type': 'quiz_message',
                'message': data
            }
        )

    async def quiz_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    # @database_sync_to_async
    # def save_answer(self, question_id, selected_choice_id):
    #     user = self.scope["user"]
    #     question = Question.objects.get(pk=question_id)
    #     selected_choice = Choice.objects.get(pk=selected_choice_id)
    #     user_competition = UserCompetition.objects.get(user_profile=user, competition_id=self.competition_id)

    #     UserAnswer.objects.create(
    #         user_competition=user_competition,
    #         question=question,
    #         selected_choice=selected_choice
    #     )

