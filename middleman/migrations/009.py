# noinspection PyProtectedMember
def migrate(store):
    
    if store.db_type == "postgres":

        store._execute("""
        CREATE TABLE IF NOT EXISTS IncomingEvents (
            id SERIAL NOT NULL,
            user_id VARCHAR(80) NOT NULL,
            room_id VARCHAR(80) NOT NULL,
            event_id VARCHAR(80) NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT fk_IncomingEvents_Users_user_id
                FOREIGN KEY (user_id)
                REFERENCES Users (anon_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE)
        """)
    else:
        store._execute("""
        CREATE TABLE IF NOT EXISTS `IncomingEvents` (
            `id` INT NOT NULL,
            `user_id` VARCHAR(80) NOT NULL,
            `room_id` VARCHAR(80) NOT NULL,
            `event_id` VARCHAR(80) NOT NULL,
            PRIMARY KEY (`id`),
            CONSTRAINT `fk_IncomingEvents_Users_user_id`
                FOREIGN KEY (`user_id`)
                REFERENCES `Users` (`anon_id`)
                ON DELETE CASCADE
                ON UPDATE CASCADE)
        """)