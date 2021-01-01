CREATE TABLE IF NOT EXISTS finished_games (
    id INTEGER PRIMARY KEY,
    image_path TEXT NOT NULL,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    num_pieces INTEGER NOT NULL,
    num_intended_pieces INTEGER NOT NULL,
    elapsed_seconds REAL NOT NULL,
    start_time TIMESTAMP,
    piece_rotation BOOLEAN DEFAULT 0,
    cheated BOOLEAN DEFAULT 0,
    snap_distance REAL NOT NULL
);
