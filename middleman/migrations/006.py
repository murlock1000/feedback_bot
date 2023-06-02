# noinspection PyProtectedMember
def migrate(store):
    
    if store.db_type == "postgres":
        store._execute("""
                DROP TABLE IF EXISTS TimelineEvents;
                """)
        store._execute("""
                DROP TABLE IF EXISTS TicketsStaffRelation;
                """)
        store._execute("""
                DROP TABLE IF EXISTS Tickets;
                """)
        store._execute("""
                DROP TABLE IF EXISTS Users;
                        """)
        store._execute("""
                DROP TABLE IF EXISTS Staff;
                        """)

        store._execute("""
            CREATE TABLE IF NOT EXISTS Users (
  user_id VARCHAR(80) NOT NULL,
  anon_id VARCHAR(80) NOT NULL UNIQUE,
  room_id VARCHAR(80) NULL,
  PRIMARY KEY (user_id))
        """)
        store._execute("""
            CREATE TABLE IF NOT EXISTS Staff (
  user_id VARCHAR(80) NOT NULL,
  PRIMARY KEY (user_id))
        """)
        store._execute("""
            CREATE TABLE IF NOT EXISTS Tickets (
  id SERIAL NOT NULL,
  user_id VARCHAR(80) NOT NULL,
  user_room_id VARCHAR(80) NULL,
  status VARCHAR(100) NULL DEFAULT 'open',
  ticket_name VARCHAR(100) NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_Tickets_Users_user_id
    FOREIGN KEY (user_id)
    REFERENCES Users (anon_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
        """)
        store._execute("""
            CREATE TABLE IF NOT EXISTS TicketsStaffRelation (
  staff_id VARCHAR(80) NOT NULL,
  ticket_id INT NOT NULL,
  PRIMARY KEY (staff_id, ticket_id),
  CONSTRAINT fk_TicketsStaffRelation_Staff_user_id
    FOREIGN KEY (staff_id)
    REFERENCES Staff (user_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_TicketsStaffRelation_Tickets_id
    FOREIGN KEY (ticket_id)
    REFERENCES Tickets (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
        """)
        store._execute("""
            CREATE TABLE IF NOT EXISTS TimelineEvents (
  id INT NOT NULL,
  device_id VARCHAR(80) NULL,
  event_id VARCHAR(80) NULL,
  room_id VARCHAR(80) NULL,
  session_id VARCHAR(80) NULL,
  event TEXT NULL,
  user_id VARCHAR(80) NULL DEFAULT '',
  ticket_id INT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_TimelineEvents_Tickets_id
    FOREIGN KEY (ticket_id)
    REFERENCES Tickets (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
        """)
    else:
        store._execute("""
                  DROP TABLE IF EXISTS TimelineEvents;
                  """)
        store._execute("""
                  DROP TABLE IF EXISTS TicketsStaffRelation;
                  """)
        store._execute("""
                  DROP TABLE IF EXISTS Tickets;
                  """)
        store._execute("""
                  DROP TABLE IF EXISTS Users;
                          """)
        store._execute("""
                  DROP TABLE IF EXISTS Staff;
                          """)

        store._execute("""
                  CREATE TABLE IF NOT EXISTS `Users` (
        `user_id` VARCHAR(80) NOT NULL,
        `room_id` VARCHAR(80) NULL,
        PRIMARY KEY (`user_id`))
              """)

        store._execute("""
                  CREATE TABLE IF NOT EXISTS `Staff` (
        `user_id` VARCHAR(80) NOT NULL,
        PRIMARY KEY (`user_id`))
              """)

        store._execute("""
                  CREATE TABLE IF NOT EXISTS `Tickets` (
        `id` INT NOT NULL,
        `user_id` VARCHAR(80) NOT NULL,
        `user_room_id` VARCHAR(80) NULL,
        `status` VARCHAR(100) NULL DEFAULT 'open',
        `ticket_name` VARCHAR(100) NULL,
        PRIMARY KEY (`id`),
        CONSTRAINT `fk_Tickets_Users_user_id`
          FOREIGN KEY (`user_id`)
          REFERENCES `Users` (`user_id`)
          ON DELETE CASCADE
          ON UPDATE CASCADE)
              """)

        store._execute("""
                  CREATE TABLE IF NOT EXISTS `TicketsStaffRelation` (
        `staff_id` VARCHAR(80) NOT NULL,
        `ticket_id` INT NOT NULL,
        PRIMARY KEY (`staff_id`, `ticket_id`),
        CONSTRAINT `fk_TicketsStaffRelation_Staff_user_id`
          FOREIGN KEY (`staff_id`)
          REFERENCES `Staff` (`user_id`)
          ON DELETE CASCADE
          ON UPDATE CASCADE,
        CONSTRAINT `fk_TicketsStaffRelation_Tickets_id`
          FOREIGN KEY (`ticket_id`)
          REFERENCES `Tickets` (`id`)
          ON DELETE CASCADE
          ON UPDATE CASCADE)
              """)

        store._execute("""
                  CREATE TABLE IF NOT EXISTS `TimelineEvents` (
        `id` INT NOT NULL,
        `device_id` VARCHAR(80) NULL,
        `event_id` VARCHAR(80) NULL,
        `room_id` VARCHAR(80) NULL,
        `session_id` VARCHAR(80) NULL,
        `event` MEDIUMTEXT NULL,
        `user_id` VARCHAR(80) NULL DEFAULT '',
        `ticket_id` INT NOT NULL,
        PRIMARY KEY (`id`),
        CONSTRAINT `fk_TimelineEvents_Tickets_id`
          FOREIGN KEY (`ticket_id`)
          REFERENCES `Tickets` (`id`)
          ON DELETE CASCADE
          ON UPDATE CASCADE)
              """)

    store._execute("""
                    CREATE INDEX fk_Tickets_Users_user_id_idx ON Tickets (user_id);
                """)
    store._execute("""
                    CREATE INDEX fk_TimelineEvents_Tickets_id_idx ON TimelineEvents (ticket_id);
                """)
    store._execute("""
                   CREATE INDEX fk_TicketsStaffRelation_Tickets_id_idx ON TicketsStaffRelation (ticket_id);
                """)
    store._execute("""
                    CREATE INDEX User_Tickets ON Tickets (user_id, id);
                """)