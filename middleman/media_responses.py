import logging
from typing import List

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomSendError

from middleman.chat_functions import send_media_to_room, send_reaction, send_text_to_room, find_private_msg
from middleman.event_responses import Message
from middleman.handlers.EventStateHandler import EventStateHandler, RoomType, LogLevel
from middleman.handlers.MessagingHandler import MessagingHandler
from middleman.models.Chat import Chat
from middleman.models.IncomingEvent import IncomingEvent
from middleman.models.Repositories.TicketRepository import TicketStatus
from middleman.models.Ticket import Ticket
from middleman.models.User import User
from middleman.utils import get_in_reply_to

logger = logging.getLogger(__name__)

media_name = {
    "m.image": "image",
    "m.audio": "audio",
    "m.video": "video",
    "m.file": "file",
}


class Media(Message):
    def __init__(self, client, store, config, room, event, media_type, body, media_url, media_file, media_info):
        """Initialize a new Media

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters
            
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageMedia): The event defining the media

            media_type (str): The type of the media

            body (str): The body of the media

            media_url (str): The url of the media

            media_file (str): The url of the encrypted media

            media_info (str): The metadata of the media
        """
        super().__init__(client, store, config, room, event)
        
        self.media_type = media_type
        self.body = body
        self.media_url = media_url
        self.media_file = media_file
        self.media_info = media_info

    async def handle_management_room_media(self):
        reply_to = get_in_reply_to(self.event)

        if reply_to and self.config.relay_management_media:
            # Send back to original sender
            message = self.store.get_message_by_management_event_id(reply_to)
            if message:
                # Relay back to original sender
                response = await send_media_to_room(
                    self.client,
                    message["room_id"],
                    self.media_type,
                    self.body,
                    self.media_url,
                    self.media_file,
                    self.media_info
                )
                if isinstance(response, RoomSendResponse):
                    # Store our outbound reply so we can reference it later
                    self.store.store_message(
                        event_id=response.event_id,
                        management_event_id=self.event.event_id,
                        room_id=message["room_id"],
                    )
                    if self.config.confirm_reaction:
                        management_room_text = self.config.confirm_reaction_success
                    elif self.config.anonymise_senders:
                        management_room_text = f"{media_name[self.media_type]} delivered back to the sender."
                    else:
                        management_room_text = f"{media_name[self.media_type]} delivered back to the sender in " \
                                               f"room {message['room_id']}."
                    logger.info(
                        f"{media_name[self.media_type]} {self.event.event_id} relayed back to the original sender",
                    )
                else:
                    if self.config.confirm_reaction:
                        management_room_text = self.config.confirm_reaction_fail
                    else:
                        management_room_text = f"Failed to send {media_name[self.media_type]} back to sender:" \
                            f"{response.message if isinstance(response, RoomSendError) else response}"
                    logger.warning(management_room_text)
                # Confirm in management room
                if self.config.confirm_reaction:
                    await send_reaction(
                        self.client,
                        self.room.room_id,
                        self.event.event_id,
                        management_room_text
                    )
                else:
                    await send_text_to_room(
                        self.client,
                        self.room.room_id,
                        management_room_text,
                        True,
                    )
            else:
                logger.debug(
                    f"Skipping {media_name[self.media_type]} {self.event.event_id} "
                    f"which is not a reply to one of our relay messages",
                )
        else:
            logger.debug(f"Skipping {self.event.event_id} reply {media_name[self.media_type]}")

    def construct_received_message(self):
        return "Bot received media for {} | "\
            f"(named: {self.room.is_named}, name: {self.room.name}, "\
            f"alias: {self.room.canonical_alias}): {self.body}"
            
    def anonymise_text(self, anonymise: bool) -> str:
        user = User.get_existing(self.store, self.event.sender)
        
        if user is None:
            user = User.create(self.store, self.event.sender)
            
        if anonymise:
            text = None
        else:
            text = f"{user.anon_id} (`{self.room.room_id}`) " \
                   f"sent {media_name[self.media_type]} {self.body}:"
        return text

    async def send_message_to_room(self, text, room_id):
        
        if not self.client.rooms.get(room_id, None):
            task = (self.client.callbacks._media, room_id, self.event.room_id, self.event)
            if task[1] not in self.client.callbacks.rooms_pending:
                self.client.callbacks.rooms_pending[task[1]] = []

            self.client.callbacks.rooms_pending[task[1]].append(task)
            return
        
        
        sender_notify_event_id = None
        if text:
            response = await send_text_to_room(self.client, room_id, text, notice=True)
            sender_notify_event_id = response.event_id
            if type(response) != RoomSendResponse or not response.event_id:
                logger.error(f"Failed to relay {media_name[self.media_type]} {self.event.event_id} to"
                         f"room {self.handler.user.room_id}")
                return

        response = await send_media_to_room(
            self.client,
            room_id,
            self.media_type,
            self.body,
            self.media_url,
            self.media_file,
            self.media_info
        )

        if type(response) == RoomSendResponse and response.event_id:
            try:
                await self.put_related_clone_event(room_id, response.event_id)
                self.store.store_message(
                    self.event.event_id,
                    response.event_id,
                    room_id,
                )
            except:
                # When cloning messages after creating a new ticket room - messages will be sent again with identical event ids.
                pass
            logger.info(f"{media_name[self.media_type]} {self.event.event_id} relayed to room {self.handler.user.room_id}")
        else:
            logger.error(f"Failed to relay {media_name[self.media_type]} {self.event.event_id} to"
                         f"room {self.handler.user.room_id}")

    def relay_based_on_mention_room(self) -> bool:
        # First check if we want to relay this
        if self.handler.is_mention_only_room([self.room.canonical_alias, self.room.room_id], self.room.is_named):
            # skip media in mention only rooms for now
            logger.debug(f"Skipping {media_name[self.media_type]} %s in room %s as it's set to "
                         f"only relay on mention and mentions are not supported for media ",
                         self.event.event_id, self.room.room_id)
            return False
        return True