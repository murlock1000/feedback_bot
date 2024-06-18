import logging
import re
from typing import Union

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomSendError, AsyncClient, RoomMessage
from nio.rooms import MatrixRoom

from feedback_bot.event_responses import Message
from feedback_bot.bot_commands import Command
from feedback_bot.chat_functions import send_reaction, send_text_to_room
from feedback_bot.config import Config
from feedback_bot.models.User import User
from feedback_bot.storage import Storage
from feedback_bot.utils import USER_ID_REGEX, get_in_reply_to, get_mentions, get_replaces, get_reply_msg, get_raise_msg

logger = logging.getLogger(__name__)


class TextMessage(Message):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, room: MatrixRoom, event: RoomMessage, message_content: str):
        """Initialize a new Text Message

        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message
            
            message_content (str): The body of the message
        """
        super().__init__(client, store, config, room, event)
        
        self.message_content: str = message_content

    async def handle_management_room_message(self):
        reply_to = get_in_reply_to(self.event)
        replaces = get_replaces(self.event)


        reply_section = get_reply_msg(self.event, reply_to, replaces)
        raise_section = get_raise_msg(self.event, reply_to, replaces)

        if not reply_section:
            if not raise_section:
                logger.debug(
                    f"Skipping {self.event.event_id} which does not look like a reply"
                )
                return
            #raise_text = raise_section[raise_section.find("!raise ") + 7:]
            #logger.debug(f"RAISE: {raise_text}")
            if reply_to:
                #message = self.store.get_message_by_management_event_id(reply_to)
               # if message:
                # Match user id in message to raise the ticket for
                reply_rx_pattern = r'> <@([^:>]+):([^>]+)> ([^\s]+)' # Chatgpt helps here
                match = re.search(reply_rx_pattern, self.event.body)
                if match:
                    rx_id = match[3]  # Get the id from regex group
                    if self.client.user_id in rx_id:
                        await send_text_to_room(
                            self.client,
                            self.room.room_id,
                            "Unable to raise tickets for media files.",
                            True,
                        )
                        return
                    command = Command(self.client, self.store, self.config, raise_section[1:7]+rx_id+raise_section[6:], self.room, self.event)
                    await command.process()

        elif reply_to:
            # Send back to original sender
            message = self.store.get_message_by_management_event_id(reply_to)
            if not message:
                logger.debug(
                    f"Skipping message {self.event.event_id} which is not a reply to one of our relay messages",
                )
                return
            # Relay back to original sender
            # Send back anything after !reply
            reply_text = reply_section[reply_section.find("!reply ") + 7:]
            response = await send_text_to_room(
                self.client,
                message["room_id"],
                reply_text,
                False,
                reply_to_event_id=message["event_id"],
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
                    management_room_text = "Message delivered back to the sender."
                else:
                    management_room_text = f"Message delivered back to the sender in room {message['room_id']}."
                logger.info(f"Message {self.event.event_id} relayed back to the original sender")
            elif isinstance(response, RoomSendError):
                if self.config.confirm_reaction:
                    management_room_text = self.config.confirm_reaction_fail
                else:
                    management_room_text = f"Failed to send message back to sender: {response.message}"
                logger.warning(management_room_text)
            else:
                if self.config.confirm_reaction:
                    management_room_text = self.config.confirm_reaction_fail
                else:
                    management_room_text = f"Failed to send message back to sender: {response}"
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
        elif replaces:
            # Edit the already sent reply event
            message = self.store.get_message_by_management_event_id(replaces)
            if not message:
                logger.debug(
                    f"Skipping message {self.event.event_id} which is not an edit to one of our reply messages",
                )
                return
            # Edit the previously sent event
            # Send back anything after !reply
            reply_text = reply_section[reply_section.find("!reply ") + 7:]
            response = await send_text_to_room(
                self.client,
                message["room_id"],
                reply_text,
                False,
                replaces_event_id=message["event_id"],
            )
            if isinstance(response, RoomSendResponse):
                # Store our outbound reply so we can reference it later
                self.store.store_message(
                    event_id=response.event_id,
                    management_event_id=self.event.event_id,
                    room_id=message["room_id"],
                )
                if self.config.anonymise_senders:
                    management_room_text = "Edit delivered back to the sender."
                else:
                    management_room_text = f"Edit delivered back to the sender in " \
                                            f"room {message['room_id']}."
                logger.info(f"Edit {self.event.event_id} relayed back to the original sender")
            elif isinstance(response, RoomSendError):
                management_room_text = f"Failed to send edit back to sender: {response.message}"
                logger.warning(management_room_text)
            else:
                management_room_text = f"Failed to send edit back to sender: {response}"
                logger.warning(management_room_text)
            # Confirm in management room
            await send_text_to_room(
                self.client,
                self.room.room_id,
                management_room_text,
                True,
            )

    def construct_received_message(self) -> str:
        return "Bot message received for {} | "\
            f"(named: {self.room.is_named}, name: {self.room.name}, "\
            f"alias: {self.room.canonical_alias}): {self.message_content}"

    def anonymise_text(self, anonymise: bool) -> str:
        user = User.get_existing(self.store, self.event.sender)
        
        if user is None:
            user = User.create(self.store, self.event.sender)
        
        if anonymise:
            text = f"{self.message_content}".replace("\n", "  \n")
        else:
            text = f"{user.anon_id} (`{self.room.room_id}`): " \
                   f"{self.message_content}".replace("\n", "  \n")
        return text
        
    async def send_message_to_room(self, text:str, room_id:str):
        
        if not self.client.rooms.get(room_id, None):
            task = (self.client.callbacks._message, room_id, self.event.room_id, self.event)
            if task[1] not in self.client.callbacks.rooms_pending:
                self.client.callbacks.rooms_pending[task[1]] = []

            self.client.callbacks.rooms_pending[task[1]].append(task)
            return
            
        reply_to_event_id, text = await self.transform_reply(text, room_id)
        replaces_event_id, text = await self.transform_replaces(text, room_id)

        response = await send_text_to_room(self.client,
                                           room_id, text,
                                           False,
                                           reply_to_event_id=reply_to_event_id,
                                           replaces_event_id=replaces_event_id,
                                        )
        if type(response) == RoomSendResponse and response.event_id:
            
            try:
                await self.put_related_clone_event(room_id, response.event_id)
                self.store.store_message(
                    self.event.event_id,
                    response.event_id,
                    self.room.room_id,
                )
            except:
                # When cloning messages after creating a new ticket room - messages will be sent again with identical event ids.
                pass
            logger.info("Message %s relayed to room %s", self.event.event_id, self.room.room_id)
        else:
            logger.error("Failed to relay message %s to room %s", self.event.event_id, self.room.room_id)


    def relay_based_on_mention_room(self) -> bool:
        if self.handler.is_mention_only_room([self.room.canonical_alias, self.room.room_id], self.room.is_named):
            # Did we get mentioned?
            mentioned = self.config.user_id in get_mentions(self.message_content) or \
                        self.message_content.lower().find(self.config.user_localpart.lower()) > -1
            if not mentioned:
                logger.debug("Skipping message %s in room %s as it's set to only relay on mention and we were not "
                             "mentioned.", self.event.event_id, self.room.room_id)
                return False
            logger.info("Room %s marked as mentions only and we have been mentioned, so relaying %s",
                        self.room.room_id, self.event.event_id)
        return True