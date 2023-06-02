from middleman.storage import Storage

class ChatRepository(object):
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def create_chat(self, user_id: str, chat_room_id: str):
        self.storage._execute("""
            INSERT INTO Chats (user_id, chat_room_id) values (?, ?);
        """, (user_id, chat_room_id,))

    def get_chat(self, chat_room_id: str):
        self.storage._execute("SELECT chat_room_id FROM Chats WHERE chat_room_id= ?;", (chat_room_id,))
        chat_room_id = self.storage.cursor.fetchone()
        if chat_room_id:
            return chat_room_id[0]
        return chat_room_id

    def assign_staff_to_chat(self, chat_room_id: str, staff_id: str):
        self.storage._execute("""
            insert into ChatsStaffRelation (chat_room_id, staff_id) values (?, ?);
        """, (chat_room_id, staff_id,))

    def get_assigned_staff(self, chat_room_id: str):
        self.storage._execute("""
            SELECT staff_id FROM ChatsStaffRelation WHERE chat_room_id = ?;
        """, (chat_room_id,))
        staff = self.storage.cursor.fetchall()
        return [
            {
                "user_id": row[0],
            } for row in staff
        ]

    def remove_staff_from_chat(self, chat_room_id: str, staff_id: str):
        self.storage._execute("""
            DELETE FROM ChatsStaffRelation WHERE chat_room_id= ? AND staff_id= ?
        """, (chat_room_id, staff_id))

    def get_all_fields(self, chat_room_id: str):
        self.storage._execute("""
            select chat_room_id, user_id from Chats where chat_room_id = ?;
        """, (chat_room_id,))
        row = self.storage.cursor.fetchone()

        return {
            "chat_room_id": row[0],
            "user_id": row[1],
        }