import logging
import re
from typing import List, Tuple, Union

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomSendError, AsyncClient, RoomMessage, RoomGetEventResponse
from nio.rooms import MatrixRoom
from nio.events.room_events import RoomMessageText

from feedback_bot.bot_commands import Command
from feedback_bot.chat_functions import send_reaction, send_text_to_room
from feedback_bot.config import Config
from feedback_bot.handlers.EventStateHandler import EventStateHandler, LogLevel, RoomType
from feedback_bot.handlers.MessagingHandler import MessagingHandler
from feedback_bot.models.EventPairs import EventPair, SingleEvent
from feedback_bot.models.IncomingEvent import IncomingEvent
from feedback_bot.storage import Storage
from feedback_bot.utils import _get_reply_msg, get_in_reply_to, get_mentions, get_replaces, get_reply_msg, get_raise_msg

logger = logging.getLogger(__name__)


class Message(object):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, room: MatrixRoom, event: RoomMessage):
        """Initialize a new Message

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessage): The event defining the message
        """
        self.client: AsyncClient = client
        self.store: Storage = store
        self.config: Config = config
        self.room:MatrixRoom  = room
        self.event: RoomMessage = event
        
        self.handler = EventStateHandler(client, store, config, room, event)
        self.messageHandler = MessagingHandler(self.handler)
        
    def construct_received_message(self) -> str:
        raise NotImplementedError

    async def handle_management_room_message(self):
        raise NotImplementedError

    async def process(self):
        """
        Process messages.
        - if management room, identify replies and forward back to original messages.
        - anything else, relay to management room.
        """

        # Update required state based on room type
        if not await self.handler.find_room_state():
            return

        msg = self.construct_received_message()

        # Combined message form
        msg = msg.format(self.handler.for_room)
        self.handler.log_console(msg, LogLevel.DEBUG)

        # Handle different scenarios
        if self.handler.room_type == RoomType.ManagementRoom:
            await self.handle_management_room_message()
        elif self.handler.room_type == RoomType.TicketRoom:
            await self.handle_ticket_room_message()
        elif self.handler.room_type == RoomType.ChatRoom:
            await self.handle_chat_room_message()
        else:
            # Default - message from user
            await self.relay_from_user()

    def save_incoming_event(self):
        incoming_event = IncomingEvent(self.store, self.handler.user.anon_id, self.room.room_id, self.event.event_id)
        incoming_event.store_incoming_event()

    def anonymise_text(self, anonymise: bool) -> str:
        raise NotImplementedError

    async def get_related(self, related_event_id: str) -> Union[str, None]:
        resp = await self.client.room_get_event(self.room.room_id, related_event_id)
        if isinstance(resp, RoomGetEventResponse):
            related_event_is_clone = resp.event.sender == self.client.user_id
        else:
            return None
        
        if related_event_is_clone:
            event_pair =  EventPair.get_clone_event_pair(self.store, self.room.room_id, related_event_id)
            if event_pair:
                return event_pair.event_id
        else:
            event_pair =  EventPair.get_event_pair(self.store, self.room.room_id, related_event_id)
            if event_pair:
                return event_pair.clone_event_id

    async def put_related_clone_event(self, clone_room_id: str, clone_event_id: str):
        event_pair = EventPair(self.store, self.room.room_id, self.event.event_id, clone_room_id, clone_event_id)
        event_pair.store_event_pair()
        
    async def transform_reply(self, text:str, room_id:str) -> Tuple[str, str]:
        reply_to_event_id = get_in_reply_to(self.event)
        if reply_to_event_id:
            reply_to_event_id = await self.get_related(reply_to_event_id)
            if reply_to_event_id:
                text = _get_reply_msg(self.event)
                
        return [reply_to_event_id, text]
    
    async def transform_replaces(self, text:str, room_id:str) -> Tuple[str, str]:
        replaces_event_id = get_replaces(self.event)
        if replaces_event_id:
            replaces_event_id = await self.get_related(replaces_event_id)
            if replaces_event_id:
                text = _get_reply_msg(self.event)
                
        return (replaces_event_id, text)
        
    async def send_message_to_room(self, text, room):
        raise NotImplementedError
     
    async def handle_ticket_room_message(self):
        """Relay staff Ticket message to the client communications room."""
        if not await self.messageHandler.handle_ticket_message():
            return

        text = self.anonymise_text(True)
        await self.send_message_to_room(text, self.handler.user.room_id)

    async def handle_chat_room_message(self):
        """Relay staff Chat message to the client communications room."""
        if not await self.messageHandler.handle_chat_message():
            return

        text = self.anonymise_text(True)
        await self.send_message_to_room(text, self.handler.user.room_id)

    def relay_based_on_mention_room(self) -> bool:
        raise NotImplementedError

    async def relay_from_user(self):
        """Relay to appropriate room (Ticket/chat/management)."""

        # First check if we want to relay this
        if not self.relay_based_on_mention_room():
            return

        # Update state for different scenarios and get room id to relay message to.
        room_id = await self.messageHandler.setup_relay()

        # Handle different relaying scenarios
        if self.handler.ticket:
            text = self.anonymise_text(True)
        elif self.handler.user.current_chat_room_id:
            text = self.anonymise_text(True)
        else:
            # Save the message event id into storage, to be sent to a ticket room later
            self.save_incoming_event()
            text = self.anonymise_text(self.config.anonymise_senders)
        await self.send_message_to_room(text, room_id)
