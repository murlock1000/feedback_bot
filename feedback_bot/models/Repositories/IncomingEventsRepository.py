from feedback_bot.storage import Storage

class IncomingEventsRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage

    def get_incoming_events(self, anon_id:str):
        self.storage._execute("""
            SELECT room_id, event_id FROM IncomingEvents WHERE user_id = ?;
        """, (anon_id,))
        incoming_events = self.storage.cursor.fetchall()
        return [
            {
                "room_id": row[0],
                "event_id": row[1],
            } for row in incoming_events
        ]
    
    def put_incoming_event(self, anon_id:str, room_id:str, event_id:str):
        self.storage._execute("""
            INSERT INTO IncomingEvents (user_id, room_id, event_id) values (?, ?, ?);
        """, (anon_id, room_id, event_id,))
    
    def delete_user_incoming_events(self, anon_id:str):
        self.storage._execute("""
            DELETE FROM IncomingEvents WHERE user_id= ?;
        """, (anon_id,))