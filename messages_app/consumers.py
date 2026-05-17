import json

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

from .models import Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):

        data = json.loads(text_data)

        message = data.get('message')
        sender_id = str(data.get('sender_id'))

        ids = self.room_name.split('_')

        user1 = await sync_to_async(User.objects.get)(id=ids[0])
        user2 = await sync_to_async(User.objects.get)(id=ids[1])

        sender = await sync_to_async(User.objects.get)(id=sender_id)

        if str(sender.id) == str(user1.id):
            receiver = user2
        else:
            receiver = user1

        # SAVE MESSAGE
        saved_message = await sync_to_async(Message.objects.create)(
            sender=sender,
            receiver=receiver,
            message=message
        )

        # SEND MESSAGE TO ROOM
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': str(sender.id),
                'sender_username': sender.username,
                'timestamp': saved_message.timestamp.strftime("%I:%M %p")
            }
        )

    async def chat_message(self, event):

        await self.send(text_data=json.dumps({

            'message': event['message'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp']

        }))