# noinspection PyProtectedMember
def migrate(store):
    store._execute("""
        ALTER TABLE Users ADD current_ticket_id INT NULL
    """)
    store._execute("""
        ALTER TABLE Users ADD CONSTRAINT fk_Users_Tickets_ticket_id FOREIGN KEY(current_ticket_id) REFERENCES Tickets(id)
    """)

