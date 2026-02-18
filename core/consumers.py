import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time private chat."""

    async def connect(self):
        self.user = self.scope['user']
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Create a consistent room name (smaller id first)
        user_ids = sorted([self.user.id, int(self.other_user_id)])
        self.room_name = f'chat_{user_ids[0]}_{user_ids[1]}'

        # Join room group
        await self.channel_layer.group_add(self.room_name, self.channel_name)

        # Mark user as online
        await self.set_online_status(True)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_name'):
            # Leave room group
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

        # Mark user as offline
        await self.set_online_status(False)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'chat_message')

        if msg_type == 'chat_message':
            message_content = data.get('message', '').strip()
            if not message_content:
                return
            message = await self.save_message(message_content)
            await self.channel_layer.group_send(
                self.room_name,
                {
                    'type': 'chat_message',
                    'message': message_content,
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'timestamp': message.timestamp.strftime('%I:%M %p'),
                    'message_id': message.id,
                }
            )

        elif msg_type == 'mark_read':
            await self.mark_messages_read()
            await self.channel_layer.group_send(
                self.room_name,
                {
                    'type': 'messages_read',
                    'reader_id': self.user.id,
                }
            )

        elif msg_type == 'typing':
            # Broadcast typing status to the other user
            await self.channel_layer.group_send(
                self.room_name,
                {
                    'type': 'typing_indicator',
                    'sender_id': self.user.id,
                    'is_typing': data.get('is_typing', False),
                }
            )

        elif msg_type == 'delete_message':
            message_id = data.get('message_id')
            if message_id:
                deleted = await self.delete_message(message_id)
                if deleted:
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            'type': 'message_deleted',
                            'message_id': message_id,
                            'deleted_by': self.user.id,
                        }
                    )

    # ── Group event handlers ──────────────────────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
        }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'reader_id': event['reader_id'],
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'sender_id': event['sender_id'],
            'is_typing': event['is_typing'],
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by'],
        }))

    # ── DB helpers ────────────────────────────────────────────────────────

    @database_sync_to_async
    def save_message(self, content):
        from .models import Message, User
        receiver = User.objects.get(id=self.other_user_id)
        return Message.objects.create(
            sender=self.user,
            receiver=receiver,
            content=content,
        )

    @database_sync_to_async
    def mark_messages_read(self):
        from .models import Message
        Message.objects.filter(
            sender_id=self.other_user_id,
            receiver=self.user,
            is_read=False,
        ).update(is_read=True)

    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete a message only if the current user is the sender."""
        from .models import Message
        deleted_count, _ = Message.objects.filter(
            id=message_id,
            sender=self.user,
        ).delete()
        return deleted_count > 0

    @database_sync_to_async
    def set_online_status(self, is_online):
        from .models import User
        User.objects.filter(id=self.user.id).update(
            is_online=is_online,
            last_seen=timezone.now(),
        )


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for broadcasting online status."""

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = 'online_status'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Broadcast that this user is online
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'is_online': True,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

            # Broadcast that this user is offline
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'is_online': False,
                }
            )

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'is_online': event['is_online'],
        }))
