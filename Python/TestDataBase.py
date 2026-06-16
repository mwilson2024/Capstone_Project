import sqlite3
from pathlib import Path


DB_FOLDER = Path(r"C:\CSI4999")
DB_NAME = "supra_protege.db"
DB_PATH = DB_FOLDER / DB_NAME


def create_database():
    DB_FOLDER.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    try:
        # Foreign keys must be OFF before dropping tables
        cursor.execute("PRAGMA foreign_keys = OFF;")

        cursor.executescript("""
        DROP TABLE IF EXISTS image_ranking;
        DROP TABLE IF EXISTS photos_content;
        DROP TABLE IF EXISTS filter_photos;
        DROP TABLE IF EXISTS photos;
        DROP TABLE IF EXISTS guests;
        DROP TABLE IF EXISTS qrcodes;
        DROP TABLE IF EXISTS event;
        DROP TABLE IF EXISTS location;
        DROP TABLE IF EXISTS app_user;

        CREATE TABLE app_user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE location (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            venue_name TEXT NOT NULL,
            street TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            zip TEXT NOT NULL,
            searchable INTEGER NOT NULL DEFAULT 0 CHECK (searchable IN (0, 1)),
            uploads_active INTEGER NOT NULL DEFAULT 0 CHECK (uploads_active IN (0, 1))
        );

        CREATE TABLE event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            location_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            password_hash TEXT NOT NULL,

            CONSTRAINT fk_event_owner
                FOREIGN KEY (owner_id)
                REFERENCES app_user(user_id),

            CONSTRAINT fk_event_location
                FOREIGN KEY (location_id)
                REFERENCES location(location_id)
        );

        CREATE TABLE qrcodes (
            qr_code_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
            expires_at TEXT NOT NULL,
            max_uploads INTEGER NOT NULL DEFAULT 10,
            upload_count INTEGER NOT NULL DEFAULT 0,
            created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            purpose TEXT NOT NULL DEFAULT 'N/A',

            CONSTRAINT fk_qrcodes_event
                FOREIGN KEY (event_id)
                REFERENCES event(event_id)
                ON DELETE CASCADE
        );

        CREATE TABLE guests (
            guest_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            phone_number TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            event_id INTEGER NOT NULL,
            can_post INTEGER NOT NULL DEFAULT 0 CHECK (can_post IN (0, 1)),
            email TEXT,

            CONSTRAINT guests_event_id_fkey
                FOREIGN KEY (event_id)
                REFERENCES event(event_id)
                ON DELETE CASCADE
        );

        CREATE TABLE photos (
            photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            photo_taken TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_edit TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            user_id INTEGER,
            guest_id INTEGER,

            CONSTRAINT photos_guest_id_fkey
                FOREIGN KEY (guest_id)
                REFERENCES guests(guest_id)
                ON DELETE SET NULL,

            CONSTRAINT photos_user_id_fkey
                FOREIGN KEY (user_id)
                REFERENCES app_user(user_id)
                ON DELETE SET NULL
        );

        CREATE TABLE filter_photos (
            filter_id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending',
            blur_score REAL NOT NULL DEFAULT 0,
            bright_score REAL NOT NULL DEFAULT 0,
            contrast_score REAL NOT NULL DEFAULT 0,
            width TEXT NOT NULL DEFAULT '0',
            height TEXT NOT NULL DEFAULT '0',
            user_approved INTEGER NOT NULL DEFAULT 0 CHECK (user_approved IN (0, 1)),
            image_hash TEXT NOT NULL,

            CONSTRAINT filter_photos_photo_id_fkey
                FOREIGN KEY (photo_id)
                REFERENCES photos(photo_id)
                ON DELETE CASCADE
        );

        CREATE TABLE photos_content (
            content_id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            person_count INTEGER NOT NULL DEFAULT 0,
            max_person_conf REAL NOT NULL DEFAULT 0,
            obj_class TEXT NOT NULL DEFAULT 'unknown',
            confidence REAL NOT NULL DEFAULT 0,
            content_score INTEGER NOT NULL DEFAULT 0,

            CONSTRAINT photos_content_photo_id_fkey
                FOREIGN KEY (photo_id)
                REFERENCES photos(photo_id)
                ON DELETE CASCADE
        );

        CREATE TABLE image_ranking (
            ranker_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            caption TEXT NOT NULL,
            mood_label TEXT NOT NULL,
            mood_conf_score REAL NOT NULL DEFAULT 0,
            all_mood_labels TEXT NOT NULL,
            keyword_score REAL NOT NULL DEFAULT 0,
            keywords TEXT NOT NULL,
            nudity_check INTEGER NOT NULL DEFAULT 0 CHECK (nudity_check IN (0, 1)),
            all_mood_scores TEXT NOT NULL,
            photo_id INTEGER NOT NULL,

            CONSTRAINT image_ranking_photo_id_fkey
                FOREIGN KEY (photo_id)
                REFERENCES photos(photo_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS storyboard_items (
            storyboard_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            photo_id INTEGER NOT NULL,
            sequence_order INTEGER NOT NULL,
            scene_label TEXT NOT NULL,
            confidence REAL DEFAULT 0,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (event_id) REFERENCES event(idevent),
            FOREIGN KEY (photo_id) REFERENCES photos(photo_id)
        );

        CREATE INDEX idx_event_owner_id ON event(owner_id);
        CREATE INDEX idx_event_location_id ON event(location_id);
        CREATE INDEX idx_qrcodes_event_id ON qrcodes(event_id);
        CREATE INDEX idx_guests_event_id ON guests(event_id);
        CREATE INDEX idx_photos_event_id ON photos(event_id);
        CREATE INDEX idx_photos_user_id ON photos(user_id);
        CREATE INDEX idx_photos_guest_id ON photos(guest_id);
        CREATE INDEX idx_filter_photos_photo_id ON filter_photos(photo_id);
        CREATE INDEX idx_photos_content_photo_id ON photos_content(photo_id);
        CREATE INDEX idx_image_ranking_photo_id ON image_ranking(photo_id);
        """)

        connection.commit()

        # Re-enable foreign keys after schema creation
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Optional: verify foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]

        print(f"Database created successfully at: {DB_PATH}")
        print(f"Foreign keys enabled: {bool(fk_status)}")

    except sqlite3.Error as e:
        connection.rollback()
        print(f"SQLite error creating database: {e}")

    finally:
        connection.close()


def seed_photos_from_folder(photoPath = "C:/CSI4999/Photos"):
    """
    Optional test loader.
    This inserts every image from C:\\CSI4999\\Photos into the photos table
    using default values for scores/status.
    """
    PHOTO_DIR = Path(photoPath)
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    if not PHOTO_DIR.exists():
        print(f"Photo folder does not exist: {PHOTO_DIR}")
        connection.close()
        return

    files = [
        file for file in PHOTO_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in image_extensions
    ]

    for file in files:
        cursor.execute("""
        INSERT INTO photos (
            event_id,
            file_name,
            file_path
        )
        VALUES (?, ?, ?);
        """, (
            int(1),
            file.name,
            str(file)
        ))

    connection.commit()
    connection.close()

    print(f"Inserted {len(files)} photo records.")

   


if __name__ == "__main__":
    create_database()
    seed_photos_from_folder(r'C:\CSI4999\Videos\Frames\videoID1')
