import logging
import re
from typing import Union

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomSendError, AsyncClient, RoomMessage, RoomRedactResponse, RoomGetEventResponse
from nio.rooms import MatrixRoom
from nio.events.room_events import RoomMessageText

from feedback_bot.event_responses import Message
from feedback_bot.chat_functions import send_room_redact
from feedback_bot.config import Config
from feedback_bot.models.User import User
from feedback_bot.storage import Storage

logger = logging.getLogger(__name__)


class RedactMessage(Message):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, room: MatrixRoom, event: RoomMessage, redacts_event_id: str, reason: str):
        """Initialize a new Redact Message

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message
            
            redacts_event_id (str): The redacted event id
            
            reason (str): The reason for redacting the event
            
        """
        super().__init__(client, store, config, room, event)
        
        self.redacts_event_id: str = redacts_event_id
        self.reason: str = reason

    async def handle_management_room_message(self):
        return
    
    def construct_received_message(self) -> str:
        return "Bot redact event received for {} | "\
            f"(named: {self.room.is_named}, name: {self.room.name}, "\
            f"alias: {self.room.canonical_alias}): {self.redacts_event_id}"

    def anonymise_text(self, anonymise: bool) -> str:
        user = User.get_existing(self.store, self.event.sender)
        
        if user is None:
            user = User.create(self.store, self.event.sender)
            
        if anonymise:
            text = f"{self.redacts_event_id}".replace("\n", "  \n")
        else:
            text = f"{user.anon_id} (`{self.room.room_id}`): " \
                   f"{self.redacts_event_id}".replace("\n", "  \n")
        return text
        
        
    async def send_message_to_room(self, text:str, room_id:str):
                
        redacts_event_id = await self.get_related(self.redacts_event_id)
        
        if not redacts_event_id:
            logger.error("Failed to find related redacts event by %s in room %s", self.event.event_id, self.room.room_id)
            return
        
        response = await send_room_redact(self.client,
                                           room_id,
                                           redacts_event_id,
                                           self.reason
                                        )
        if type(response) == RoomRedactResponse and response.event_id:
            logger.info("Redact message %s relayed to room %s", self.event.event_id, self.room.room_id)
        else:
            logger.error("Failed to relay redact message %s to room %s", self.event.event_id, self.room.room_id)


    def relay_based_on_mention_room(self) -> bool:
        return True