from __future__ import annotations
import logging

# noinspection PyPackageRequirements
from nio import (RoomSendResponse, 
                 RoomCreateResponse, 
                 RoomInviteResponse,
                 RoomCreateError,
                 RoomGetEventResponse,
                 AsyncClient,
                 RoomMessageNotice,
                 RoomMessageFormatted,
                 RoomMessageMedia,
                 RoomEncryptedMedia
                )
from nio.rooms import MatrixRoom
from nio.events.room_events import RoomMessageText

from middleman import commands_help
from middleman.chat_functions import create_private_room, invite_to_room, send_text_to_room, kick_from_room, \
    find_private_msg, is_user_in_room, send_shared_history_keys
from middleman.config import Config
from middleman.handlers.EventStateHandler import EventStateHandler, LogLevel, RoomType
from middleman.handlers.MessagingHandler import MessagingHandler
from middleman.models.Chat import Chat
from middleman.models.EventPairs import EventPair
from middleman.models.IncomingEvent import IncomingEvent
from middleman.models.Repositories.TicketRepository import TicketStatus, TicketRepository
from middleman.models.Staff import Staff
from middleman.models.Support import Support
from middleman.models.Ticket import Ticket
from middleman.models.User import User
from middleman.storage import Storage
from middleman.utils import get_replaces, get_username

logger = logging.getLogger(__name__)


class Command(object):
    def __init__(self, client: AsyncClient, store: Storage, config: Config, command: str, room: MatrixRoom, event: RoomMessageText):
        """A command made by a user

        Args:
            client (nio.AsyncClient): The client to communicate to matrix with

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            command (str): The command and arguments

            room (nio.rooms.MatrixRoom): The room the command was sent in

            event (nio.events.room_events.RoomMessageText): The event describing the command
        """
        self.client: AsyncClient = client
        self.store: Storage = store
        self.config: Config = config
        self.command: str = command
        self.room: MatrixRoom = room
        self.event: RoomMessageText = event
        self.args = self.command.split()[1:]
        self.handler = EventStateHandler(client, store, config, room, event)
        self.messageHandler = MessagingHandler(self.handler)

    async def process(self):

        # Update required state based on room type
        if not await self.handler.find_room_state():
            return

        if not self.handler.find_state_staff():
            msg = f"User in room {self.room.room_id} | {self.room.name} \
            is unauthorized to use {self.command}"
            await self.handler.message_management(msg, LogLevel.INFO)
            return

        """Process the command"""
        if self.command.startswith("echo"):
            await self._echo()
        elif self.command.startswith("help"):
            await self._show_help()
        #elif self.command.startswith("message"):
        #    await self._message()
        elif self.command.startswith("claimfor"):
            await self._claimfor()
        elif self.command.startswith("claim"):
            await self._claim()
        elif self.command.startswith("raise"):
            await self._raise_ticket()
        elif self.command.startswith("close"):
            await self._close_room()
        elif self.command.startswith("forceclose"):
            await self._force_close()
        elif self.command.startswith("reopen"):
            await self._reopen_ticket()
        elif self.command.startswith("opentickets"):
            await self._open_tickets()
        elif self.command.startswith("activeticket"):
            await self._show_active_user_ticket()
        elif self.command.startswith("addstaff"):
            await self._add_staff()
        #elif self.command.startswith("setupcommunicationsroom"):
        #    await self._setup_communications_room()
        #elif self.command.startswith("chat"):
        #    await self._chat()
        else:
            await self._unknown_command()

    # ## Decorators
    # def with_staff(f):
    #     async def wrapper(self, *args, **kwargs):
    #         self.handler.staff = Staff.get_existing(self.store, self.event.sender)
    #         if self.handler.staff:
    #             await f(self, *args, **kwargs)
    #         else:
    #             logger.info(f"{self.event.sender} is not staff and tried executing staff command.")
    #             await send_text_to_room(
    #                 self.client, self.config.management_room_id,
    #                 f"User is not authorized to use this command",
    #             )
    #             return
    #     return wrapper

    ## Commands

    async def _echo(self):
        """Echo back the command's arguments"""
        response = " ".join(self.args)
        await send_text_to_room(self.client, self.room.room_id, response)

    async def _show_help(self):
        """Show the help text"""
        if not self.args:
            text = (
                "Hello, I am a feedback bot. Use `help commands` to view "
                "available commands."
            )
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        help_messages = {
            "commands":commands_help.AVAILABLE_COMMANDS,
            #"message":commands_help.COMMAND_WRITE,
            "claimfor": commands_help.COMMAND_CLAIMFOR,
            "claim":commands_help.COMMAND_CLAIM,
            "raise":commands_help.COMMAND_RAISE,
            "close":commands_help.COMMAND_CLOSE,
            "reopen":commands_help.COMMAND_REOPEN,
            "opentickets":commands_help.COMMAND_OPEN_TICKETS,
            "activeticket":commands_help.COMMAND_ACTIVE_TICKET,
            "addstaff":commands_help.COMMAND_ADD_STAFF,
            #"setupcommunicationsroom":commands_help.COMMAND_SETUP_COMMUNICATIONS_ROOM,
            #"chat":commands_help.COMMAND_CHAT,

        }
        topic = self.args[0]
        text = help_messages.get(topic,"Unknown help topic!")
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )

    #TODO refactor direct messaging
    async def _message(self):
        """
        Write a m.text message to a room.
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow sending messages from the management room
            return

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_WRITE)
            return

        replaces = get_replaces(self.event)
        replaces_event_id = None
        if replaces:
            message = self.store.get_message_by_management_event_id(replaces)
            if message:
                replaces_event_id = message["event_id"]

        room = self.args[0]
        # Remove the command
        text = self.command[7:]
        # Remove the room
        text = text.replace(room, "", 1)
        # Strip the leading spaces
        text = text.strip()

        response = await send_text_to_room(self.client, room, text, False, replaces_event_id=replaces_event_id)

        if type(response) == RoomSendResponse and response.event_id:
            self.store.store_message(
                event_id=response.event_id,
                management_event_id=self.event.event_id,
                room_id=room,
            )
            if replaces_event_id:
                logger.info(f"Processed editing message in room {room}")
                await send_text_to_room(self.client, self.room.room_id, f"Message was edited in {room}")
            else:
                logger.info(f"Processed sending message to room {room}")
                await send_text_to_room(self.client, self.room.room_id, f"Message was delivered to {room}")
            return

        error_message = response if type(response == str) else getattr(response, "message", "Unknown error")
        await send_text_to_room(
            self.client, self.room.room_id, f"Failed to deliver message to {room}! Error: {error_message}",
        )

    async def _open_tickets(self):
        """
        No args - List all open tickets
        Arg provided - List all open tickets assigned to staff member
        """
        ticket_rep: TicketRepository = self.store.repositories.ticketRep

        if len(self.args) == 1:
            staff = Staff.get_existing(self.store, self.args[0])
            if not staff:
                await send_text_to_room(
                    self.client, self.room.room_id, f"{self.args[0]} is not a staff member.",
                )
                return
            open_tickets = ticket_rep.get_open_tickets_of_staff(staff.user_id)
        else:
            open_tickets = ticket_rep.get_open_tickets()

        # Construct response array
        resp = [f"<p>{ticket['id']} - {ticket['ticket_name']} - {ticket['anon_id']}</p>" for ticket in open_tickets]
        resp = "".join(resp)

        await send_text_to_room(
            self.client, self.room.room_id, f"Open tickets: \n{resp}",
        )

    async def _show_active_user_ticket(self):
        """
        Print active ticket of user
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ACTIVE_TICKET)
            return

        anon_id = self.args[0]

        user = User.get_by_anon_id(self.store, anon_id)
        if not user:
            await send_text_to_room(
                self.client, self.room.room_id, f"User with ID {anon_id} does not exist in DB",
            )
            return

        await send_text_to_room(
            self.client, self.room.room_id, f"{user.current_ticket_id}",
        )

    async def _add_staff(self):
        """
        Add staff
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow adding staff from the management room
            return

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ADD_STAFF)
            return

        user_id = self.args[0]

        Staff.create_new(self.store, user_id)
        await send_text_to_room(
            self.client, self.room.room_id, f"{user_id} is now staff.",
        )

    async def _setup_communications_room(self):
        """
        Updates the communications room of a user. Creates one if needed.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_SETUP_COMMUNICATIONS_ROOM)
            return

        user_id = self.args[0]

        user = User.get_existing(self.store, user_id)
        if not user:
            # If we don't have the user details yet - create new instance
            user = User.create_new(self.store, user_id)

        room = find_private_msg(self.client, user_id)

        if room:
            user.update_communications_room(room.room_id)
            await send_text_to_room(
                self.client, self.room.room_id, f"Existing room found with ID {room.room_id}",
            )
            return

        username = get_username(self.client.user_id)
        if not username:
            await send_text_to_room(
                self.client, self.room.room_id, f"Invalid mxid {self.client.user_id}",
            )

        resp = await create_private_room(self.client, user_id, username)
        if isinstance(resp, RoomCreateResponse):
            user.update_communications_room(resp.room_id)
            await send_text_to_room(
                self.client, self.room.room_id,
                f"Created a new DM for user {user_id} with roomID: {resp.room_id}",
            )
        elif isinstance(resp, RoomCreateError):
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to create a new DM for user {user_id} with error: {resp.status_code}",
            )

    async def _copy_incoming_events(self, ticket:Ticket):
        incomingEvents = IncomingEvent.get_incoming_events(self.store, ticket.anon_id)
        for event in incomingEvents:
            
            # Delete old paired events to prevent original message being tied to different clones
            EventPair.delete_event(self.store, event.room_id, event.event_id)
            
            resp = await self.client.room_get_event(event.room_id, event.event_id)
            if isinstance(resp, RoomGetEventResponse):
                if isinstance(resp.event, (RoomMessageText, RoomMessageNotice, RoomMessageFormatted)):
                    task = (self.client.callbacks._message, ticket.ticket_room_id, event.room_id, resp.event)
                elif isinstance(resp.event, (RoomMessageMedia, RoomEncryptedMedia)):
                    task = (self.client.callbacks._media, ticket.ticket_room_id, event.room_id, resp.event)
                else:
                    continue
                
                # 0 - task method
                # 1 - room that is blocking the task
                # 2 - room the event originated from
                # 3 - the event itself
                
                if task[1] in self.client.rooms:
                    await task[0](self.client.rooms[task[2]], task[3])
                else:
                    if task[1] not in self.client.callbacks.rooms_pending:
                        self.client.callbacks.rooms_pending[task[1]] = []

                    self.client.callbacks.rooms_pending[task[1]].append(task)
            else:
                user = User.get_existing(self.store, event.anon_id)
                if user is None:
                    user = User.create_new(self.store, event.anon_id)
                msg = f"Failed to get event {event.event_id} from user {user.anon_id} in room {event.room_id}. Event was not copied to new room."
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
        
        # Delete the events
        IncomingEvent.delete_user_incoming_events(self.store, event.anon_id)

    async def _raise_ticket(self):
        """
        Staff raise a ticket for a user.
        """

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_RAISE)
            return

        anon_id = self.args[0]
        # Remove the command
        text = self.command[6:]
        # Remove the user_id
        text = text.replace(anon_id, "", 1)
        # Strip the leading spaces
        text = text.strip()

        # Find User by anon_id
        user = User.get_by_anon_id(self.store, anon_id)

        if not user:
            msg = f"Failed to raise Ticket: User not found."
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return

        # Raise a new ticket
        if text:
            ticket = Ticket.create_new(self.store, user.anon_id, text)
        else:
            ticket = Ticket.create_new(self.store, user.anon_id)

        if ticket:
            user.update_current_ticket_id(ticket.id)

            msg = f"Raised Ticket #{ticket.id} {ticket.ticket_name} for {user.anon_id}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            if self.room.room_id != self.config.management_room_id:
                await send_text_to_room(self.client, self.config.management_room_id,msg,)
        else:
            msg = f"Failed to raise Ticket. Index was not created in DB."
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return

        # Create a room for this ticket and invite staff to it
        response = await ticket.create_ticket_room(self.client, [self.handler.staff.user_id])
        if isinstance(response, RoomCreateResponse):
            logger.info(f"Created a Ticket room {response.room_id} successfully for ticket id {ticket.id}")
        else:
            msg = f"Failed to create a room for ticket id {ticket.id}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return
          
        # Claim Ticket for the staff
        ticket.claim_ticket(self.handler.staff.user_id)

        # Invite staff to Ticket room
        # response = await ticket.invite_to_ticket_room(self.client, self.handler.staff.user_id)

        # Send user messages sent to management room to ticket room.
        await self._copy_incoming_events(ticket)

        #if isinstance(response, RoomInviteResponse):
        #    logger.info(f"Invited staff {self.handler.staff.user_id} to room {ticket.ticket_room_id}")
        #else:
        #    msg = f"Failed to invite staff {self.handler.staff.user_id} to room {ticket.ticket_room_id}"
        #    logger.info(msg)
        #    await send_text_to_room(
        #        self.client, self.room.room_id, msg,
        #    )
        #    return

    async def _chat(self):
        """
        Staff create a chat with user.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CHAT)
            return

        user_id = self.args[0]

        # Find User by user_id
        user = User.get_existing(self.store, user_id)

        if not user:
            username = get_username(user_id)
            if not username:
                msg = f"Failed to chat with {user_id}, user does not exist"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                return
            else:
                user = User.create_new(self.store, user_id)

        # Fetch existing or create new Chat for user:
        if user.current_chat_room_id:
            chat = Chat.get_existing(self.store, user.current_chat_room_id)
            if not chat:
                msg = f"Unable to find chat with ID {user.current_chat_room_id} in DB of {user_id}"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                return
        else:
            response = await Chat.create_new(self.store, self.client, user.user_id)
            if isinstance(response, RoomCreateError):
                msg = f"Failed to create Room: {response.status_code}"
                logger.error(msg)
                await send_text_to_room(
                    self.client, self.room.room_id, msg,
                )
                return
            elif isinstance(response, Exception):
                logger.error(f"Failed to store Chat with error: {response}")
                return

            chat = response
            user.update_current_chat_room_id(chat.chat_room_id)

            msg = f"Created Chat {chat.chat_room_id} for {chat.user_id}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            if self.room.room_id != self.config.management_room_id:
                await send_text_to_room(self.client, self.config.management_room_id, msg,)

        # Claim Chat for staff
        chat.claim_chat(self.handler.staff.user_id)

        # Invite staff to the Chat room
        response = await chat.invite_to_chat_room(self.client, self.handler.staff.user_id)

        if isinstance(response, RoomInviteResponse):
            logger.info(f"Invited staff {self.handler.staff.user_id} to chat room {chat.chat_room_id}")
        else:
            msg = f"Failed to invite staff {self.handler.staff.user_id} to chat room {chat.chat_room_id}"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return

    async def _close_room(self):
        if self.handler.room_type == RoomType.ChatRoom:
            await self._close_chat()
        else:
            await self._close_ticket()

    async def _close_chat(self):
        """
        Staff close the current Chat.
        """

        chat:Chat = Chat.find_chat_of_room(self.store, self.room)
        if not chat:
            msg = f"Could not find Chat of room {self.room.room_id} to close"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
            return
        current_user_chat_room_id = chat.find_user_current_chat_room_id()

        if current_user_chat_room_id == chat.chat_room_id:
            chat.userRep.set_user_current_chat_room_id(chat.user_id, None)

        msg = f"Closed Chat {chat.chat_room_id}"
        logger.info(msg)
        await send_text_to_room(self.client, self.room.room_id, msg,)
        if self.room.room_id != self.config.management_room_id:
            await send_text_to_room(self.client, self.config.management_room_id, msg,)
        # Kick staff from room after close
        await kick_from_room(
            self.client, self.event.sender, self.room.room_id
        )

    async def _force_close(self):
        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CHAT)
            return
        
        ticket_id = self.args[0]
        
        ticket:Ticket = Ticket.get_existing(self.store, ticket_id)
        if not ticket:
            msg = f"Could not find Ticket with ticket id {ticket_id} to forcefully close"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
        else:
            if ticket.status != TicketStatus.CLOSED:
                ticket.set_status(TicketStatus.CLOSED)

                current_user_ticket_id = ticket.find_user_current_ticket_id()
                if current_user_ticket_id == ticket.id:
                    ticket.userRep.set_user_current_ticket_id(ticket.anon_id, None)

                msg = f"Forcefully closed Ticket {ticket.id}"
                logger.info(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                if self.room.room_id != self.config.management_room_id:
                    await send_text_to_room(self.client, self.config.management_room_id, msg,)
                    
            else:
                msg = f"Ticket {ticket.id} is already closed"
                logger.info(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)

        

    async def _close_ticket(self):
        """
        Staff close the current ticket.
        """

        ticket:Ticket = Ticket.find_ticket_of_room(self.store, self.room)
        if not ticket:
            msg = f"Could not find Ticket with ticket room {self.room.room_id} to close"
            logger.warning(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)
        else:
            if ticket.status != TicketStatus.CLOSED:
                ticket.set_status(TicketStatus.CLOSED)

                current_user_ticket_id = ticket.find_user_current_ticket_id()
                if current_user_ticket_id == ticket.id:
                    ticket.userRep.set_user_current_ticket_id(ticket.anon_id, None)

                msg = f"Closed Ticket {ticket.id}"
                logger.info(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                if self.room.room_id != self.config.management_room_id:
                    await send_text_to_room(self.client, self.config.management_room_id, msg,)

                # Kick all support from the room
                support_users = ticket.get_assigned_support()
                
                for support in support_users:
                    await kick_from_room(
                    self.client, support, self.room.room_id
                )
                
                # Kick staff from room after close
                await kick_from_room(
                    self.client, self.event.sender, self.room.room_id
                )
            else:
                msg = f"Ticket {ticket.id} is already closed"
                logger.info(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)

    async def _reopen_ticket(self):
        """
        Staff reopen the current ticket, or specify and be reinvited to it.
        """

        if len(self.args) > 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_REOPEN)
            return

        # Find ticket by room or provided ID
        if len(self.args) == 0:
            ticket: Ticket = Ticket.find_ticket_of_room(self.store, self.room)
            if not ticket:
                msg = f"Could not find Ticket with ticket room {self.room.room_id} to reopen"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                return
        else:
            ticket_id = self.args[0]
            if not ticket_id.isnumeric():
                msg = f"Ticket ID must be a whole number"
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                return

            ticket_id = int(ticket_id)
            ticket = Ticket.get_existing(self.store, ticket_id)

            if not ticket:
                msg = f"Ticket with ID {ticket_id} does not exist."
                logger.warning(msg)
                await send_text_to_room(self.client, self.room.room_id, msg,)
                return

        current_user_ticket_id = ticket.find_user_current_ticket_id()
        if current_user_ticket_id is not None:
            msg = f"User already has Ticket open with ID {current_user_ticket_id} close it first to reopen this Ticket."
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return
        if ticket.status == TicketStatus.CLOSED:
            ticket.set_status(TicketStatus.OPEN)
            ticket.userRep.set_user_current_ticket_id(ticket.anon_id, ticket.id)

            msg = f"Reopened Ticket {ticket.id}"
            logger.info(msg)
            await send_text_to_room(
                self.client, self.room.room_id, msg,)

            if self.room.room_id != self.config.management_room_id:
                await send_text_to_room(self.client, self.config.management_room_id, msg,)

            if self.room.room_id != ticket.ticket_room_id:
                await send_text_to_room(self.client, ticket.ticket_room_id, msg,)

            # Invite staff to the ticket room if not joined already
            room = self.client.rooms.get(ticket.ticket_room_id, None)
            if room and self.handler.staff:
                if not is_user_in_room(room, self.handler.staff.user_id):
                    resp = await invite_to_room(self.client, self.handler.staff.user_id, room.room_id)

                    if isinstance(resp, RoomInviteResponse):
                        await send_shared_history_keys(self.client, room.room_id, [self.handler.staff.user_id])

        else:
            msg = f"Ticket {ticket.id} is already open"
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)

    async def _claim(self):
        """
        Staff claim a ticket.
        """

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CLAIM)
            return

        ticket_id = self.args[0]

        # Get ticket by id
        ticket = Ticket.get_existing(self.store, int(ticket_id))

        if not ticket:
            msg = f"Ticket with ID {ticket_id} was not found."
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return

        # Claim Ticket for the staff
        ticket.claim_ticket(self.handler.staff.user_id)

        logger.debug(f"Inviting user {self.handler.staff.user_id} to ticket room {ticket.ticket_room_id}")

        # Invite staff to Ticket room
        response = await ticket.invite_to_ticket_room(self.client, self.handler.staff.user_id)

        if isinstance(response, RoomInviteResponse):
            await send_shared_history_keys(self.client, ticket.ticket_room_id, [self.handler.staff.user_id])
            logger.debug(f"Invited staff to Ticket room successfully")
        else:
            msg = f"Failed to invite {self.handler.staff.user_id} to Ticket room {ticket.ticket_room_id}: {response.message}"
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            
    async def _claimfor(self):
        """
        Staff claim a ticket for support.
        """

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CLAIMFOR)
            return

        user_id = self.args[0]
        ticket_id = self.args[1]

        # Get ticket by id
        ticket = Ticket.get_existing(self.store, int(ticket_id))

        if not ticket:
            msg = f"Ticket with ID {ticket_id} was not found."
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            return
        
        support = Support.get_existing(self.store, user_id)
        
        if not support:
            msg = f"Creating new support user for {user_id}."
            logger.info(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)
            
            support = Support.create_new(self.store, user_id)

        # Claim Ticket for the support user
        ticket.claimfor_ticket(support.user_id)

        logger.debug(f"Inviting user {support.user_id} to ticket room {ticket.ticket_room_id}")

        # Invite support to Ticket room
        response = await ticket.invite_to_ticket_room(self.client, support.user_id)

        if isinstance(response, RoomInviteResponse):
            await send_shared_history_keys(self.client, ticket.ticket_room_id, [support.user_id])
            logger.debug(f"Invited support to Ticket room successfully")
        else:
            msg = f"Failed to invite {support.user_id} to Ticket room {ticket.ticket_room_id}: {response.message}"
            logger.warning(msg)
            await send_text_to_room(self.client, self.room.room_id, msg,)

