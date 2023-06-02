import logging
from enum import Enum
from typing import List

from nio import AsyncClient, MatrixRoom, RoomMessage

from middleman.chat_functions import send_text_to_room
from middleman.config import Config
from middleman.models.Chat import chat_room_name_pattern, Chat
from middleman.models.Staff import Staff
from middleman.models.Ticket import ticket_name_pattern, Ticket
from middleman.models.User import User
from middleman.storage import Storage

class RoomType(Enum):
    ManagementRoom  = 0
    LoggingRoom     = 1
    UserRoom        = 2
    TicketRoom      = 3
    ChatRoom        = 4

class LogLevel(Enum):
    INFO            = 0
    WARNING         = 1
    ERROR           = 2
    DEBUG           = 3


logger = logging.getLogger(__name__)

# Class for holding room and event handling methods, state
class EventStateHandler(object):

    def __init__(self, client:AsyncClient, store:Storage, config:Config, room:MatrixRoom, event:RoomMessage):
        self.client = client
        self.store = store
        self.config = config
        self.room = room
        self.event = event

        # Determine room event is in
        self.room_type = self.determine_room_type(self.room)

        # Variables for holding Event State
        self.user: User|None = None
        self.staff: Staff|None = None

        self.ticket: Ticket|None = None
        self.chat: Chat|None = None

        # Variables for holding Logging utils
        self.for_room = f"room {self.room.display_name}"


    # State fetchers, return True on successfully finding state

    def find_state_user(self) -> bool:
        if self.room_type == RoomType.UserRoom:
            self.user = User.get_existing(self.store, self.event.sender)

        return self.user is not None
    def find_state_staff(self) -> bool:
        self.staff = Staff.get_existing(self.store, self.event.sender)

        return self.staff is not None
    def find_state_ticket(self) -> bool:
        if self.room_type == RoomType.TicketRoom:
            self.ticket = Ticket.find_ticket_of_room(self.store, self.room)

        # Update logging format
        if self.ticket:
            self.for_room = f"Ticket #{self.ticket.id} in room {self.room.display_name}"
        return self.ticket is not None
    def find_state_chat(self) -> bool:
        if self.room_type == RoomType.ChatRoom:
            self.chat = Chat.find_chat_of_room(self.store, self.room)

        # Update logging format
        if self.chat:
            self.for_room = f"Chat: {self.chat.chat_room_id}"

        return self.chat is not None

    def find_state_management(self) -> bool:
        if not self.room.room_id == self.config.management_room_id:
            return False

        # Update logging format
        self.for_room = f"Management room: {self.room.room_id}"
        return True

    def find_state_user_room(self) -> bool:
        # Update logging format
        self.for_room = f"User room: {self.room.room_id}"
        return True

    # Creation of new state
    def create_state_user(self):
        self.user = User.create_new(self.store, self.event.sender)

    def update_state_user(self, anon_id:str):
        self.user = User.get_by_anon_id(self.store, anon_id)

    def update_state_ticket(self, ticket_id:int):
        self.ticket = Ticket.get_existing(self.store, ticket_id)

    def update_state_chat(self, chat_room_id:str):
        self.chat = Chat.get_existing(self.store, chat_room_id)

    async def find_room_state(self) -> bool:

        if self.room_type == RoomType.TicketRoom:
            # Try to find existing ticket
            if not self.find_state_ticket():
                await self.message_room(f"Error: Failed to find ticket of this room")
                return False
        elif self.room_type == RoomType.ChatRoom:
            # Try to find existing chat
            if not self.find_state_chat():
                await self.message_room(f"Error: Failed to find chat of this room")
                return False
        elif self.room_type == RoomType.ManagementRoom:
            if not self.find_state_management():
                await self.message_room(f"Error: Not a valid Management room")
                return False
        elif self.room_type == RoomType.UserRoom:
            if not self.find_state_user_room():
                await self.message_management(f"Error: failed to set state for {self.room.room_id}")
                return False
        else:
            return False

        return True

    def is_mention_only_room(self, identifiers: List[str], is_named: bool) -> bool:
        """
        Check if this room is only if mentioned.
        """
        if self.config.mention_only_always_for_named and is_named:
            return True
        for identifier in identifiers:
            if identifier in self.config.mention_only_rooms:
                return True
        return False


    # Room type determined by the room name in most cases
    def determine_room_type(self, room: MatrixRoom) -> RoomType:

        if room.room_id == self.config.management_room_id:
            self.room_type = RoomType.ManagementRoom
        elif room.room_id == self.config.matrix_logging_room:
            self.room_type = RoomType.LoggingRoom
        elif room.name is None:
            self.room_type = RoomType.UserRoom
        elif chat_room_name_pattern.match(room.name):
            self.room_type = RoomType.ChatRoom
        elif ticket_name_pattern.match(room.name):
            self.room_type = RoomType.TicketRoom
        else:
            self.room_type = RoomType.UserRoom

        return self.room_type


    # Logging methods
    def log_console(self, msg:str, level: LogLevel):
        if level == level.INFO:
            logger.info(msg)
        if level == level.ERROR:
            logger.error(msg)
        if level == level.DEBUG:
            logger.debug(msg)
        if level == level.WARNING:
            logger.warning(msg)

    async def message_room(self, msg:str, level=LogLevel.DEBUG):
        self.log_console(msg, level)

        await send_text_to_room(self.client, self.room.room_id, msg)

    async def message_management(self, msg:str, level=LogLevel.DEBUG):
        self.log_console(msg, level)

        await send_text_to_room(self.client, self.config.management_room_id, msg)

    async def message_logging_room(self, msg:str, level=LogLevel.DEBUG):
        self.log_console(msg, level)

        await send_text_to_room(self.client, self.config.matrix_logging_room, msg)

    async def message_all(self, msg:str, level=LogLevel.DEBUG):
        self.log_console(msg, level)

        if self.room.room_id != self.config.management_room_id:
            await send_text_to_room(self.client, self.room.room_id, msg)

        await send_text_to_room(self.client, self.config.management_room_id, msg)
