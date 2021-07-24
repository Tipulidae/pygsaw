import sqlite3


def init_database(db):
    sqlite3.register_adapter(bool, int)
    sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))
    with open('sql/statistics.sql', 'r') as f:
        sql = f.read()

    cursor = db.cursor()
    cursor.executescript(sql)
    db.commit()


def save_statistics(**statistics):
    db = sqlite3.connect(
        'sql/statistics.db',
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    init_database(db)
    cursor = db.cursor()
    insert_statement = """
        INSERT INTO
            finished_games(
                image_path,
                image_width,
                image_height,
                num_pieces,
                num_intended_pieces,
                elapsed_seconds,
                start_time,
                piece_rotation,
                cheated,
                snap_distance
            ) 
        VALUES (
            :image_path, 
            :image_width,
            :image_height,
            :num_pieces,
            :num_intended_pieces,
            :elapsed_seconds,
            :start_time,
            :piece_rotation,
            :cheated,
            :snap_distance)"""

    cursor.execute(insert_statement, statistics)
    db.commit()
    db.close()
