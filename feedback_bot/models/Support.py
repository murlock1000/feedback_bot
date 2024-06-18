from feedback_bot.models.Repositories.SupportRepository import SupportRepository
from feedback_bot.storage import Storage

class Support(object):
    def __init__(self, storage:Storage, user_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.supportRep:SupportRepository = self.storage.repositories.supportRep
        self.user_id = user_id

    @staticmethod
    def get_existing(storage:Storage, user_id:str):
        # Find existing support
        exists = storage.repositories.supportRep.get_support(user_id)
        if not exists:
            return None
        else:
            return Support(storage, user_id)

    @staticmethod
    def create_new(storage:Storage, user_id:str):
        # Create Support entry if not found in DB
        storage.repositories.supportRep.create_support(user_id)
        return Support(storage, user_id)