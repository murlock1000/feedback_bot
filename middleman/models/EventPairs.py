from __future__ import annotations
from typing import List
from middleman.models.Repositories.EventPairsRepository import EventPairsRepository
from middleman.storage import Storage

class SingleEvent(object):
    def __init__(self, room_id, event_id):
        self.room_id = room_id
        self.event_id = event_id

# Controller (External data)-> Service (Logic) -> Repository (sql queries)
class EventPair(object):
    def __init__(self, storage:Storage, room_id:str, event_id:str, clone_room_id:str, clone_event_id:str):
        # Setup Storage bindings
        self.storage = storage
        self.eventPairsRep: EventPairsRepository = self.storage.repositories.eventPairsRep
        
        self.room_id = room_id
        self.event_id = event_id
        
        self.clone_room_id = clone_room_id
        self.clone_event_id = clone_event_id

    @staticmethod
    def get_event_pair(storage:Storage, room_id:str, event_id:str) -> EventPair:
        # Fetch event pair for that particular room/event combination
        result = storage.repositories.eventPairsRep.get_room_event(room_id, event_id)
        
        if result:
            result = EventPair(storage, room_id, event_id, result['clone_room_id'], result['clone_event_id'])
            
        return result
    
    @staticmethod
    def get_clone_event_pair(storage:Storage, clone_room_id:str, clone_event_id:str) -> EventPair:
        # Fetch event pair for that particular room/event clone combination
        result = storage.repositories.eventPairsRep.get_room_clone_event(clone_room_id, clone_event_id)
        
        if result:
            result = EventPair(storage, result['room_id'], result['event_id'], clone_room_id, clone_event_id)
            
        return result

    @staticmethod
    def delete_room_events(storage:Storage, room_id:str):
        storage.repositories.eventPairsRep.delete_room_events(room_id)
    
    @staticmethod
    def delete_event(storage:Storage, room_id:str, event_id:str):
        storage.repositories.eventPairsRep.delete_event(room_id, event_id)
    
    @staticmethod
    def delete_room_clone_events(storage:Storage, clone_room_id:str):
        storage.repositories.eventPairsRep.delete_room_clone_events(clone_room_id)
        
    def store_event_pair(self):
        # Store event pair to associate ticket room messages with real rooms and vice versa.
        self.eventPairsRep.put_clone_event(self.room_id, self.event_id, self.clone_room_id, self.clone_event_id)
        
    def get_single_event(self):
        return SingleEvent(self.room_id, self.event_id)
    
    def get_single_clone_event(self):
        return SingleEvent(self.clone_room_id, self.clone_event_id)
        
    