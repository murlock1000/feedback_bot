from middleman.models.Repositories.StaffRepository import StaffRepository
from middleman.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class Staff(object):
    def __init__(self, storage:Storage, user_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.staffRep:StaffRepository = self.storage.repositories.staffRep
        self.user_id = user_id

    @staticmethod
    def get_existing(storage:Storage, user_id:str):
        # Find existing staff
        exists = storage.repositories.staffRep.get_staff(user_id)
        if not exists:
            return None
        else:
            return Staff(storage, user_id)

    @staticmethod
    def create_new(storage:Storage, user_id:str):
        # Create Staff entry if not found in DB
        storage.repositories.staffRep.create_staff(user_id)
        return Staff(storage, user_id)