import sqlite3
with sqlite3.connect("gifts.db") as connection:
    c = connection.cursor()

    c.execute('DROP TABLE gift_list')
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS gift_list(
            planner_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gift_ids INTEGER,
            balance DECIMAL,
            picture TEXT
        )
        '''
    );

    c.execute('DROP TABLE logins')
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS logins(
            planner_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            password TEXT
        )
        '''
    )

    c.execute('DROP TABLE gifts')
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS gifts(
            asin TEXT,
            description TEXT,
            price DECIMAL,
            url TEXT
        )
        '''
    )