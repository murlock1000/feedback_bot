from feedback_bot.storage import Storage

class SupportRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage
        
    def create_support(self, user_id:str):
        self.storage._execute("""
            insert into Support (user_id) values (?);
        """, (user_id,))
        
    def get_support(self, user_id:str):
        self.storage._execute("SELECT user_id FROM Support WHERE user_id= ?;", (user_id,))
        id = self.storage.cursor.fetchone()
        if id:
            return id[0]
        return id
    
    def delete_support(self, user_id:str):
        self.storage._execute("""
            DELETE FROM Support WHERE user_id= ?;
        """, (user_id,))