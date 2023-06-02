from middleman.storage import Storage

class EventPairsRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage

    def get_room_event(self, room_id:str, event_id:str):
        self.storage._execute("""
            SELECT clone_room_id, clone_event_id FROM EventPairs WHERE room_id = ? AND event_id = ?;
        """, (room_id, event_id,))
        clone_event = self.storage.cursor.fetchone()
        if clone_event:
            return {
                    "clone_room_id": clone_event[0],
                    "clone_event_id": clone_event[1],
                }
        return None
    
    def get_room_clone_event(self, clone_room_id:str, clone_event_id:str):
        self.storage._execute("""
            SELECT room_id, event_id FROM EventPairs WHERE clone_room_id = ? AND clone_event_id = ?;
        """, (clone_room_id, clone_event_id,))
        event = self.storage.cursor.fetchone()
        if event:
            return {
                    "room_id": event[0],
                    "event_id": event[1],
                }
        return None
    
    def put_clone_event(self, room_id:str, event_id:str, clone_room_id:str, clone_event_id:str):
        self.storage._execute("""
            INSERT INTO EventPairs (room_id, event_id, clone_room_id, clone_event_id) values (?, ?, ?, ?);
        """, (room_id, event_id, clone_room_id, clone_event_id,))
    
    def delete_room_events(self, room_id:str):
        self.storage._execute("""
            DELETE FROM EventPairs WHERE room_id= ?;
        """, (room_id,))
    
    def delete_room_clone_events(self, clone_room_id:str):
        self.storage._execute("""
            DELETE FROM EventPairs WHERE clone_room_id= ?;
        """, (clone_room_id,))
    
    def delete_event(self, room_id:str, event_id:str):
        self.storage._execute("""
            DELETE FROM EventPairs WHERE room_id= ? AND event_id= ?;
        """, (room_id, event_id,))