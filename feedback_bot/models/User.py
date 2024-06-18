from feedback_bot.models.Repositories.UserRepository import UserRepository
from feedback_bot.storage import Storage
from feedback_bot.utils import get_username
from faker import Faker
from datetime import datetime
import random

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class User(object):
    def __init__(self, storage:Storage, user_id:str):
        # Setup storage bindings
        self.storage = storage
        self.userRep:UserRepository = self.storage.repositories.userRep

        # Fetch existing fields of User
        fields = self.userRep.get_all_fields(user_id)
        self.user_id =              fields['user_id']
        self.room_id =              fields['room_id']
        self.current_ticket_id =    fields['current_ticket_id']
        self.current_chat_room_id = fields['current_chat_room_id']
        self.anon_id = fields['anon_id']
        self.username = get_username(self.user_id)

    @staticmethod
    def get_existing(storage:Storage, user_id:str):
        # Find existing user
        exists = storage.repositories.userRep.get_user(user_id)
        if not exists:
            return None
        else:
            return User(storage, user_id)
        
    @staticmethod
    def get_by_anon_id(storage:Storage, anon_id:str):
        user_id = storage.repositories.userRep.get_by_anon_id(anon_id)
        if not user_id:
            return None
        else:
            return User(storage, user_id)

    @staticmethod
    def create_new(storage:Storage, user_id:str):
        # Create User entry if not found in DB
        anon_id = User.generate_anonymous_name()
        storage.repositories.userRep.create_user(user_id, anon_id)
        return User(storage, user_id)
    
    @staticmethod
    def generate_anonymous_name(seed = datetime.now().timestamp()):
        Faker.seed(seed)
        faker = Faker()        
        first_name = faker.first_name()
        last_name = faker.first_name()
        digits = random.randint(0, 100)
        
        return first_name + last_name + str(digits)
        
    def update_communications_room(self, room_id: str):
        self.userRep.set_user_room(self.user_id, room_id)
        self.room_id = room_id

    def update_current_ticket_id(self, current_ticket_id: int):
        self.userRep.set_user_current_ticket_id(self.anon_id, current_ticket_id)
        self.current_ticket_id = current_ticket_id

    def update_current_chat_room_id(self, current_chat_room_id: str):
        self.userRep.set_user_current_chat_room_id(self.user_id, current_chat_room_id)
        self.current_chat_room_id = current_chat_room_id