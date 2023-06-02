from typing import List
from nio import AsyncClient, RoomCreateResponse, RoomInviteResponse, MatrixRoom, Response

from middleman.chat_functions import invite_to_room, create_room, send_text_to_room
from middleman.models.Repositories.TicketRepository import TicketStatus, TicketRepository
from middleman.models.Repositories.UserRepository import UserRepository
from middleman.storage import Storage
import logging
import re
# Controller (External data)-> Service (Logic) -> Repository (sql queries)

logger = logging.getLogger(__name__)


ticket_name_pattern = re.compile(r"Ticket #(\d+) \(.+\)")

class Ticket(object):

    ticket_cache = {}

    def __init__(self, storage:Storage, ticket_id:int):
        # Setup Storage bindings
        self.storage = storage
        self.ticketRep:TicketRepository = self.storage.repositories.ticketRep
        self.userRep: UserRepository = self.storage.repositories.userRep

        # Fetch existing fields of Ticket
        fields = self.ticketRep.get_all_fields(ticket_id)

        self.id =               fields['id']
        self.anon_id =          fields['anon_id']
        self.ticket_room_id =   fields['ticket_room_id']
        self.status =           TicketStatus(fields['status'])
        self.ticket_name =      fields['ticket_name']

    @staticmethod
    def get_existing(storage: Storage, ticket_id: int):
        # Check cache first
        ticket = Ticket.ticket_cache.get(ticket_id, None)
        if ticket:
            return ticket

        # Find existing Ticket in Database
        exists = storage.repositories.ticketRep.get_ticket(ticket_id)
        if exists:
            ticket = Ticket(storage, ticket_id)
            # Add ticket to cache
            Ticket.ticket_cache[ticket_id] = ticket
            return ticket
        else:
            return None

    @staticmethod
    def create_new(storage: Storage, anon_id:str, ticket_name:str="General"):
        # Create Ticket entry
        ticket_id = storage.repositories.ticketRep.create_ticket(anon_id, ticket_name)

        if ticket_id:
            ticket = Ticket(storage, ticket_id)
            # Add ticket to cache
            Ticket.ticket_cache[ticket_id] = ticket
            return ticket
        else:
            return None

    @staticmethod
    def find_room_ticket_id(room:MatrixRoom):
        match = None
        if room.name:
            match = ticket_name_pattern.match(room.name)

        ticket_id = None
        if match:
            ticket_id = match[1]  # Get the id from regex group

        if ticket_id and ticket_id.isnumeric():
            return int(ticket_id)

    @staticmethod
    def find_ticket_of_room(store, room:MatrixRoom):
        is_open_ticket_room = False

        ticket_id = Ticket.find_room_ticket_id(room)
        if not ticket_id:
            return None

        should_add_to_cache = False
        ticket = Ticket.ticket_cache.get(ticket_id, None)
        # Cache hit
        if ticket:
            return ticket

        # Cache miss
        ticket = Ticket.get_existing(store, ticket_id)

        if ticket:
            Ticket.ticket_cache[ticket.id] = ticket
            return ticket
        else:
            return None

    async def create_ticket_room(self, client:AsyncClient, invite:List[str] = []):
        # Request a Ticket reply room to be created.
        response = await create_room(client, f"Ticket #{self.id} ({self.ticket_name})", invite)

        if isinstance(response, RoomCreateResponse):
            self.ticket_room_id = response.room_id
            self.ticketRep.set_ticket_room_id(self.id, self.ticket_room_id)

        return response

    def set_ticket_room_id(self, ticket_room_id:str):
        self.ticket_room_id = ticket_room_id
        self.ticketRep.set_ticket_room_id(self.id, ticket_room_id)

    async def invite_to_ticket_room(self, client:AsyncClient, user_id:str):
        # Invite staff to the Ticket room
        response = await invite_to_room(client, user_id, self.ticket_room_id)
        return response

    def claim_ticket(self, staff_id:str):
        # Claim the ticket for staff member

        staff = self.ticketRep.get_assigned_staff(self.id)

        # Check if staff not assigned to ticket already
        if staff_id in [s['user_id'] for s in staff]:
            return

        # Assign staff member to the ticket
        self.ticketRep.assign_staff_to_ticket(self.id, staff_id)
        
    def claimfor_ticket(self, support_id:str):
        # Claim the ticket for support member

        support = self.ticketRep.get_assigned_support(self.id)

        # Check if support not assigned to ticket already
        if support_id in [s['user_id'] for s in support]:
            return

        # Assign support member to the ticket
        self.ticketRep.assign_support_to_ticket(self.id, support_id)

    def get_assigned_support(self):
        support = self.ticketRep.get_assigned_support(self.id)

        return [s['user_id'] for s in support]

    def set_status(self, status:TicketStatus):
        self.ticketRep.set_ticket_status(self.id, status.value)
        self.status = status

        # Remove from cache if closing ticket
        if status == TicketStatus.CLOSED and Ticket.ticket_cache.get(self.id):
            Ticket.ticket_cache.pop(self.id)

    def find_user_current_ticket_id(self):
        return self.userRep.get_user_current_ticket_id(self.anon_id)
