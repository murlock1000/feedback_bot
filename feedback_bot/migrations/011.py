# noinspection PyProtectedMember
def migrate(store):

    if store.db_type == "postgres":

        store._execute("""
        CREATE TABLE IF NOT EXISTS Support (
            user_id VARCHAR(80) NOT NULL,
            PRIMARY KEY (user_id))
        """)

        store._execute("""
        CREATE TABLE IF NOT EXISTS TicketsSupportRelation (
            support_id VARCHAR(80) NOT NULL,
            ticket_id INT NOT NULL,
            PRIMARY KEY (support_id, ticket_id),
            CONSTRAINT fk_TicketsSupportRelation_Support_user_id
              FOREIGN KEY (support_id)
              REFERENCES Support (user_id)
              ON DELETE CASCADE
              ON UPDATE CASCADE,
            CONSTRAINT fk_TicketsSupportRelation_Tickets_id
              FOREIGN KEY (ticket_id)
              REFERENCES Tickets (id)
              ON DELETE CASCADE
              ON UPDATE CASCADE)
        """)
    else:
        store._execute("""
        CREATE TABLE IF NOT EXISTS `Support` (
            PRIMARY KEY (`user_id`))
            `user_id` VARCHAR(80) NOT NULL,
        """)

        store._execute("""
        CREATE TABLE IF NOT EXISTS `TicketsSupportRelation` (
            `support_id` VARCHAR(80) NOT NULL,
            `ticket_id` INT NOT NULL,
            PRIMARY KEY (`support_id`, `ticket_id`),
            CONSTRAINT `fk_TicketsSupportRelation_Support_user_id`
              FOREIGN KEY (`support_id`)
              REFERENCES `Support` (`user_id`)
              ON DELETE CASCADE
              ON UPDATE CASCADE,
            CONSTRAINT `fk_TicketsSupportRelation_Tickets_id`
              FOREIGN KEY (`ticket_id`)
              REFERENCES `Tickets` (`id`)
              ON DELETE CASCADE
              ON UPDATE CASCADE)
        """)
        
        
