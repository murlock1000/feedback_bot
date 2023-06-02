# noinspection PyProtectedMember
def migrate(store):
    
    if store.db_type == "postgres":
        store._execute("""
                DROP TABLE IF EXISTS ChatsStaffRelation;
                """)
        store._execute("""
                DROP TABLE IF EXISTS Chats;
                """)

        store._execute("""
            CREATE TABLE IF NOT EXISTS Chats (
                chat_room_id VARCHAR(80) NOT NULL,
                user_id VARCHAR(80) NOT NULL,
                PRIMARY KEY (chat_room_id),
                CONSTRAINT fk_Chats_Users_user_id
                  FOREIGN KEY (user_id)
                  REFERENCES Users (user_id)
                  ON DELETE CASCADE
                  ON UPDATE CASCADE)
            """)

        store._execute("""
            CREATE TABLE IF NOT EXISTS ChatsStaffRelation (
                staff_id VARCHAR(80) NOT NULL,
                chat_room_id VARCHAR(80) NOT NULL,
                PRIMARY KEY (staff_id, chat_room_id),
                CONSTRAINT fk_ChatsStaffRelation_Staff_user_id
                  FOREIGN KEY (staff_id)
                  REFERENCES Staff (user_id)
                  ON DELETE CASCADE
                  ON UPDATE CASCADE,
                CONSTRAINT fk_ChatsStaffRelation_Chat_id
                  FOREIGN KEY (chat_room_id)
                  REFERENCES Chats (chat_room_id)
                  ON DELETE CASCADE
                  ON UPDATE CASCADE)
        """)

    store._execute("""
        ALTER TABLE Users ADD current_chat_room_id VARCHAR(80) NULL
    """)
    store._execute("""
        ALTER TABLE Users ADD CONSTRAINT fk_Users_Chats_chat_id FOREIGN KEY(current_chat_room_id) REFERENCES Chats(chat_room_id)
    """)