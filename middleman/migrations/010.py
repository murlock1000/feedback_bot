# noinspection PyProtectedMember
def migrate(store):
    
    if store.db_type == "postgres":

        store._execute("""
        CREATE TABLE IF NOT EXISTS EventPairs (
            id SERIAL NOT NULL,
            room_id VARCHAR(80) NOT NULL,
            event_id VARCHAR(80) NOT NULL,
            clone_room_id VARCHAR(80) NOT NULL,
            clone_event_id VARCHAR(80) NOT NULL,
            PRIMARY KEY (id))
        """)
    else:
        store._execute("""
        CREATE TABLE IF NOT EXISTS `EventPairs` (
            `id` INT NOT NULL,
            `room_id` VARCHAR(80) NOT NULL,
            `event_id` VARCHAR(80) NOT NULL,
            `clone_room_id` VARCHAR(80) NOT NULL,
            `clone_event_id` VARCHAR(80) NOT NULL,
            PRIMARY KEY (`id`))
        """)
    
    store._execute("""
        CREATE INDEX event_pairs_room_ids_idx on EventPairs (room_id, clone_room_id);
    """)