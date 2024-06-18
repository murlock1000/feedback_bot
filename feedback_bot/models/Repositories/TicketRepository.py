from feedback_bot.storage import Storage
from enum import Enum

class TicketStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    IN_PROGRESS = "in_progress"
    STUCK = "STUCK"

class TicketRepository(object):
    def __init__(self, storage:Storage) -> None:
        self.storage = storage
    
    def create_ticket(self, anon_id:str, ticket_name:str):
        self.storage._execute("""
            INSERT INTO Tickets (user_id, ticket_name) values (?, ?) RETURNING id;
        """, (anon_id, ticket_name,))
        inserted_id = self.storage.cursor.fetchone()
        if inserted_id:
            return inserted_id[0] #BUG - lastrowid always returns 0??
        return inserted_id
        
    def get_ticket_id(self, anon_id:str, user_room_id: str):
        self.storage._execute("SELECT id FROM Tickets WHERE anon_id= ? AND user_room_id= ?;", (anon_id, user_room_id,))
        id = self.storage.cursor.fetchone()
        if id:
            return id[0]
        return id

    def get_ticket(self, ticket_id:int):
        self.storage._execute("SELECT id FROM Tickets WHERE id= ?;", (ticket_id, ))
        id = self.storage.cursor.fetchone()
        if id:
            return id[0]
        return id
    
    def assign_staff_to_ticket(self, ticket_id: int, staff_id:str):
        self.storage._execute("""
            insert into TicketsStaffRelation (ticket_id, staff_id) values (?, ?);
        """, (ticket_id, staff_id,))
    
    def get_assigned_staff(self, ticket_id:int):
        self.storage._execute("""
            SELECT staff_id FROM TicketsStaffRelation WHERE ticket_id = ?;
        """, (ticket_id,))
        staff = self.storage.cursor.fetchall()
        return [
            {
                "user_id": row[0],
            } for row in staff
        ]
    
    def assign_support_to_ticket(self, ticket_id: int, support_id:str):
        self.storage._execute("""
            insert into TicketsSupportRelation (ticket_id, support_id) values (?, ?);
        """, (ticket_id, support_id,))
    
    def get_assigned_support(self, ticket_id:int):
        self.storage._execute("""
            SELECT support_id FROM TicketsSupportRelation WHERE ticket_id = ?;
        """, (ticket_id,))
        support = self.storage.cursor.fetchall()
        return [
            {
                "user_id": row[0],
            } for row in support
        ]
    
    def remove_staff_from_ticket(self, ticket_id: int, staff_id:str):
        self.storage._execute("""
            DELETE FROM TicketsStaffRelation WHERE ticket_id= ? AND staff_id= ?
        """, (ticket_id, staff_id))
    
    def set_ticket_status(self, ticket_id:int, status:str):
        self.storage._execute("""
            UPDATE Tickets SET status= ? WHERE id=?
        """, (status, ticket_id))

    def get_ticket_status(self, ticket_id: int):
        self.storage._execute("""
            SELECT status FROM Tickets WHERE id=?
        """, (ticket_id,))

    def set_ticket_name(self, ticket_id:int, ticket_name:str):
        self.storage._execute("""
            UPDATE Tickets SET ticket_name= ? WHERE id=?
        """, (ticket_name, ticket_id))

    def get_ticket_name(self, ticket_id: int):
        self.storage._execute("""
            SELECT ticket_name FROM Tickets WHERE id=?
        """, (ticket_id,))

    def set_ticket_room_id(self, ticket_id:int, ticket_room_id:str):
        self.storage._execute("""
            UPDATE Tickets SET user_room_id= ? WHERE id=?
        """, (ticket_room_id, ticket_id))

    def get_ticket_room_id(self, ticket_id: int):
        self.storage._execute("""
            SELECT user_room_id FROM Tickets WHERE id=?
        """, (ticket_id,))
        ticket_room_id = self.storage.cursor.fetchone()
        if ticket_room_id:
            return ticket_room_id[0]
        return ticket_room_id

    def get_all_fields(self, ticket_id:int):
        self.storage._execute("""
            select id, user_id, user_room_id, status, ticket_name from Tickets where id = ?
        """, (ticket_id,))
        row = self.storage.cursor.fetchone()
        # TODO: rename user_room_id to ticket_room_id (specifies staff-bot communications room for the ticket)
        return {
                "id": row[0],
                "anon_id": row[1],
                "ticket_room_id": row[2],
                "status": row[3],
                "ticket_name": row[4],
            }

    def get_open_tickets(self):
        self.storage._execute("""
            SELECT id, user_id, ticket_name FROM Tickets WHERE status=?
        """, (TicketStatus.OPEN.value,))

        tickets = self.storage.cursor.fetchall()
        return [
            {
                'id':ticket[0],
                'anon_id': ticket[1],
                'ticket_name' : ticket[2],
            } for ticket in tickets
        ]

    def get_open_tickets_of_staff(self, staff_id:str):
        self.storage._execute("""
            SELECT id, user_id, ticket_name FROM Tickets t JOIN TicketsStaffRelation ts ON t.id=ts.ticket_id WHERE status=? AND staff_id=?
        """, (TicketStatus.OPEN.value, staff_id, ))

        tickets = self.storage.cursor.fetchall()
        return [
            {
                'id':ticket[0],
                'anon_id': ticket[1],
                'ticket_name' : ticket[2],
            } for ticket in tickets
        ]