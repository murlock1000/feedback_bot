from feedback_bot.models.Repositories.ChatRepository import ChatRepository
from feedback_bot.models.Repositories.EventPairsRepository import EventPairsRepository
from feedback_bot.models.Repositories.IncomingEventsRepository import IncomingEventsRepository
from feedback_bot.models.Repositories.StaffRepository import StaffRepository
from feedback_bot.models.Repositories.SupportRepository import SupportRepository
from feedback_bot.models.Repositories.TicketRepository import TicketRepository
from feedback_bot.models.Repositories.UserRepository import UserRepository
from feedback_bot.storage import Storage

class Repositories(object):
    def __init__(self, storage:Storage):
        self.storage = storage
        
        # Initialise global Repositories
        self.ticketRep = TicketRepository(self.storage)
        self.staffRep = StaffRepository(self.storage)
        self.supportRep = SupportRepository(self.storage)
        self.userRep = UserRepository(self.storage)
        self.chatRep = ChatRepository(self.storage)
        self.incomingEventsRep = IncomingEventsRepository(self.storage)
        self.eventPairsRep = EventPairsRepository(self.storage)