from django.test import TestCase
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from asgiref.testing import ApplicationCommunicator
from django.utils import timezone
from witswin.asgi import application 
from quiztap.models import Competition, Question
from quiztap.serializers import CompetitionSerializer, QuestionSerializer
import json

class QuizConsumerTestCase(TestCase):

    def setUp(self):
        self.competition = Competition.objects.create(
            title="Test Competition",
            start_at=timezone.now() - timezone.timedelta(minutes=5)
        )
        self.question = Question.objects.create(
            competition=self.competition,
            text="Sample Question",
            number=1
        )

    async def connect_to_communicator(self):
        communicator = WebsocketCommunicator(application, f"/ws/quiz/{self.competition.id}/")
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_connect(self):
        communicator, connected = await self.connect_to_communicator()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_ping_pong(self):
        communicator, connected = await self.connect_to_communicator()
        self.assertTrue(connected)

        await communicator.send_json_to({"command": "PING"})
        response = await communicator.receive_from()
        self.assertEqual(response, "PONG")

        await communicator.disconnect()

    async def test_get_competition(self):
        communicator, connected = await self.connect_to_communicator()
        self.assertTrue(connected)

        await communicator.send_json_to({"command": "GET_COMPETITION"})
        response = await communicator.receive_json_from()
        expected_data = CompetitionSerializer(instance=self.competition).data
        self.assertEqual(response, expected_data)

        await communicator.disconnect()

    async def test_get_question(self):
        communicator, connected = await self.connect_to_communicator()
        self.assertTrue(connected)

        await communicator.send_json_to({"command": "GET_QUESTION", "args": {"index": 1}})
        response = await communicator.receive_json_from()
        expected_data = QuestionSerializer(instance=self.question).data
        self.assertEqual(response, expected_data)

        await communicator.disconnect()

    async def test_get_current_question_before_start(self):
        self.competition.start_at = timezone.now() + timezone.timedelta(minutes=5)
        self.competition.save()

        communicator, connected = await self.connect_to_communicator()
        self.assertTrue(connected)

        await communicator.send_json_to({"command": "GET_QUESTION", "args": {"index": 1}})
        response = await communicator.receive_json_from()
        self.assertEqual(response, { "error": "wait for competition to begin", "data": None })

        await communicator.disconnect()

    async def test_group_send_message(self):
        communicator, connected = await self.connect_to_communicator()
        self.assertTrue(connected)

        channel_layer = get_channel_layer()
        assert channel_layer, "Channel layer must be exists"
        await channel_layer.group_send(
            f"quiz_{self.competition.id}",
            {
                'type': 'quiz_message',
                'message': 'test_message'
            }
        )
        response = await communicator.receive_json_from()
        self.assertEqual(response, {'message': 'test_message'})

        await communicator.disconnect()
