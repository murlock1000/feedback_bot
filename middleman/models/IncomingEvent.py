from __future__ import annotations
from typing import List
from middleman.models.Repositories.IncomingEventsRepository import IncomingEventsRepository
from middleman.storage import Storage

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class IncomingEvent(object):
    def __init__(self, storage:Storage, user_id:str, room_id:str, event_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.incomingEventsRep:IncomingEventsRepository = self.storage.repositories.incomingEventsRep
        
        self.anon_id = user_id
        self.room_id = room_id
        self.event_id = event_id

    @staticmethod
    def get_incoming_events(storage:Storage, anon_id:str) -> List[IncomingEvent]:
        # Fetch all incoming events from user that have not been sent to a ticket room
        result = storage.repositories.incomingEventsRep.get_incoming_events(anon_id)
        incoming_events = []
        
        for row in result:
            event = IncomingEvent(storage, anon_id, row['room_id'], row['event_id'])
            incoming_events.append(event)
            
        return incoming_events

    @staticmethod
    def delete_user_incoming_events(storage:Storage, anon_id:str):
        storage.repositories.incomingEventsRep.delete_user_incoming_events(anon_id)
        
    def store_incoming_event(self):
        # Store incoming event from user to be sent to a ticket room when created
        self.incomingEventsRep.put_incoming_event(self.anon_id, self.room_id, self.event_id)
        
    