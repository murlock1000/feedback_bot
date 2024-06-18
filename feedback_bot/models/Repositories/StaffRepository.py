from feedback_bot.storage import Storage

class StaffRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage
        
    def create_staff(self, user_id:str):
        self.storage._execute("""
            insert into Staff (user_id) values (?);
        """, (user_id,))
        
    def get_staff(self, user_id:str):
        self.storage._execute("SELECT user_id FROM Staff WHERE user_id= ?;", (user_id,))
        id = self.storage.cursor.fetchone()
        if id:
            return id[0]
        return id
    
    def delete_staff(self, user_id:str):
        self.storage._execute("""
            DELETE FROM Staff WHERE user_id= ?;
        """, (user_id,))