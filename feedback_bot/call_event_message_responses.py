import logging

# noinspection PyPackageRequirements
from nio import AsyncClient, ErrorResponse, RoomSendResponse
from nio.rooms import MatrixRoom
from nio.events.room_events import CallEvent

from feedback_bot.event_responses import Message
from feedback_bot.chat_functions import send_text_to_room
from feedback_bot.config import Config
from feedback_bot.storage import Storage
from feedback_bot.utils import with_ratelimit

logger = logging.getLogger(__name__)


class CallEventMessage(Message):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, room: MatrixRoom, event: CallEvent, event_type:str):
        """Initialize a new call invite Message

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.CallInviteEvent): The event defining the message
            
        """
        super().__init__(client, store, config, room, event)
        self.event_type = event_type

    async def handle_management_room_message(self):
        # Ignore calls from management room
        return
    
    def construct_received_message(self) -> str:
        return "Bot call event received for {} | "\
            f"(named: {self.room.is_named}, name: {self.room.name}, "\
            f"alias: {self.room.canonical_alias}): event type: {self.event_type} "

    def anonymise_text(self, anonymise: bool) -> str:
        return ""
        
    async def send_notice_to_room(self, room_id:str):
        if not self.client.rooms.get(room_id, None):
            task = (self.client.callbacks._redact, room_id, self.event.room_id, self.event)
            if task[1] not in self.client.callbacks.rooms_pending:
                self.client.callbacks.rooms_pending[task[1]] = []

            self.client.callbacks.rooms_pending[task[1]].append(task)
            return
        
        text = f"{self.event.sender} in {self.room.display_name} (`{self.room.room_id}`) " \
                   f" Is calling support.".replace("\n", "  \n")
        response = await send_text_to_room(self.client, room_id, text, False)
        
        if type(response) == RoomSendResponse and response.event_id:
            self.store.store_message(
                self.event.event_id,
                response.event_id,
                self.room.room_id,
            )
            logger.info("Call invite event %s relayed to room %s", self.event.event_id, self.room.room_id)
        else:
            logger.error("Failed to relay call invite event %s to room %s", self.event.event_id, self.room.room_id)
    
    async def send_message_to_room(self, text:str, room_id:str):
        # Send notice events to management room
        # Relay calls to any other room
        if room_id == self.config.management_room:
            if self.event_type == "m.call.invite":
                await self.send_notice_to_room(room_id)
        else:
            if not self.client.rooms.get(room_id, None):
                task = (self.client.callbacks._call_event, room_id, self.event.room_id, self.event)
                if task[1] not in self.client.callbacks.rooms_pending:
                    self.client.callbacks.rooms_pending[task[1]] = []

                self.client.callbacks.rooms_pending[task[1]].append(task)
                return

            resp = await with_ratelimit(self.client.room_send)(
                    room_id,
                    self.event.source.get("type", None),
                    self.event.source.get("content")
            )
        
            if type(resp) == ErrorResponse:
                logger.error("Failed to relay call %s to room %s", self.event.event_id, self.room.room_id)
            else:
                logger.info("Call event %s relayed to room %s", self.event.event_id, self.room.room_id)

        

    def relay_based_on_mention_room(self) -> bool:
        return True