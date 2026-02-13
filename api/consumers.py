from channels.generic.websocket import AsyncWebsocketConsumer
import json

class RewardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.userprofile_id = self.scope['url_route']['kwargs']['userprofile_id']
        self.group_name = f'userprofile_{self.userprofile_id}'
        
        print(f"WebSocket connection established for user_id: {self.userprofile_id}")
        print(f"Joining group: {self.group_name}")

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Logic to verify and handle the userprofile_id if needed
        
        await self.accept()
        print(f'UserProfile {self.userprofile_id} connected')
        print(self.scope)
        
        await self.send(text_data=json.dumps({
            'type':'welcome_message',
            'message': f'Connection established for UserProfile {self.userprofile_id}',
            'data':{'info':'Welcome!'}
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        pass



    async def receive(self, text_data):
        data = json.loads(text_data)
        text_data_json = json.loads(text_data)

        action = text_data_json.get('action', None)

        if action:
            print(f'Received action from Websocket:{action}')

        await self.send(text_data=json.dumps({
            'type':'received_data',
            'message': 'Action Recevied ',
            'data': data
        }))

    
    async def send_reward_update(self, action_data):
        
        await self.send(text_data=json.dumps({
            'type': 'reward_update',
            'message': 'Reward update received successfully!',

            'data': action_data
        }))
