import json
import sqlite3
import os
import logging
from typing import List, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def delete_database(db_path: str):
    """Safely delete the database file if it exists"""
    try:
        if os.path.exists(db_path):
            logger.info(f"Deleting existing database at {db_path}")
            os.remove(db_path)
            logger.info("Database deleted successfully")
        else:
            logger.info("No existing database found")
    except Exception as e:
        logger.error(f"Error deleting database: {str(e)}")
        raise

class TennisHotelsDB:
    def __init__(self, db_name: str = 'tennis_hotels.db'):
        self.db_name = db_name
        self.initialize_database()

    def initialize_database(self):
        """Delete existing database and create a new one"""
        # First delete existing database
        delete_database(self.db_name)
        
        logger.info("Creating new database...")
        self.setup_database()
        logger.info("Database initialized successfully")

    def setup_database(self):
        """Create the database schema if it doesn't exist"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Create hotels table with updated schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hotels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    location TEXT,
                    country TEXT,
                    source_country TEXT,
                    star_rating INTEGER,
                    rating_score REAL,
                    rating_text TEXT,
                    page_number INTEGER,
                    scrape_timestamp TEXT,
                    UNIQUE(name, location, scrape_timestamp)
                )
            ''')
            
            # Create prices table with updated schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hotel_id INTEGER,
                    amount REAL,
                    currency TEXT,
                    provider TEXT,
                    room_type TEXT,
                    cancellation_policy TEXT,
                    FOREIGN KEY (hotel_id) REFERENCES hotels(id)
                )
            ''')
            
            # Create tennis facilities table with updated schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tennis_facilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hotel_id INTEGER,
                    total_courts INTEGER,
                    lighted_courts INTEGER,
                    opening_hours TEXT,
                    court_cost TEXT,
                    lessons_available BOOLEAN,
                    lessons_cost TEXT,
                    equipment_rental BOOLEAN,
                    equipment_cost TEXT,
                    tennis_camps BOOLEAN,
                    tournaments BOOLEAN,
                    tennis_shop BOOLEAN,
                    FOREIGN KEY (hotel_id) REFERENCES hotels(id)
                )
            ''')
            
            # Create court surfaces table with updated schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS court_surfaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facility_id INTEGER,
                    surface_type TEXT,
                    court_count INTEGER,
                    FOREIGN KEY (facility_id) REFERENCES tennis_facilities(id)
                )
            ''')
            
            conn.commit()

    def insert_hotel_data(self, hotel_data: Dict):
        """Insert a single hotel's data into the database"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            try:
                # Insert hotel basic info
                cursor.execute('''
                    INSERT OR REPLACE INTO hotels 
                    (name, location, country, source_country, star_rating, 
                     rating_score, rating_text, page_number, scrape_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    hotel_data['name'],
                    hotel_data.get('location', ''),
                    hotel_data.get('country', ''),
                    hotel_data.get('source_country', ''),
                    hotel_data.get('star_rating', 0),
                    hotel_data.get('rating_score'),
                    hotel_data.get('rating_text', ''),
                    hotel_data.get('page_number', 0),
                    hotel_data.get('scrape_timestamp', datetime.now().isoformat())
                ))
                
                hotel_id = cursor.lastrowid
                
                # Insert price info
                if hotel_data.get('price'):
                    cursor.execute('''
                        INSERT INTO prices 
                        (hotel_id, amount, currency, provider, room_type, cancellation_policy)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        hotel_id,
                        hotel_data['price'].get('amount'),
                        hotel_data['price'].get('currency'),
                        hotel_data['price'].get('provider'),
                        hotel_data['price'].get('room_type'),
                        hotel_data['price'].get('cancellation_policy')
                    ))
                
                # Insert tennis facilities
                if hotel_data.get('tennis_facilities'):
                    cursor.execute('''
                        INSERT INTO tennis_facilities 
                        (hotel_id, total_courts, lighted_courts, opening_hours,
                         court_cost, lessons_available, lessons_cost,
                         equipment_rental, equipment_cost, tennis_camps,
                         tournaments, tennis_shop)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        hotel_id,
                        hotel_data['tennis_facilities'].get('total_courts', 0),
                        hotel_data['tennis_facilities'].get('lighted_courts', 0),
                        hotel_data['tennis_facilities'].get('opening_hours', ''),
                        hotel_data['tennis_facilities'].get('court_cost', ''),
                        hotel_data['tennis_facilities'].get('lessons_available', False),
                        hotel_data['tennis_facilities'].get('lessons_cost', ''),
                        hotel_data['tennis_facilities'].get('equipment_rental', False),
                        hotel_data['tennis_facilities'].get('equipment_cost', ''),
                        hotel_data['tennis_facilities'].get('tennis_camps', False),
                        hotel_data['tennis_facilities'].get('tournaments', False),
                        hotel_data['tennis_facilities'].get('tennis_shop', False)
                    ))
                    
                    facility_id = cursor.lastrowid
                    
                    # Insert court surfaces
                    if 'surface_counts' in hotel_data['tennis_facilities']:
                        for surface, count in hotel_data['tennis_facilities']['surface_counts'].items():
                            cursor.execute('''
                                INSERT INTO court_surfaces (facility_id, surface_type, court_count)
                                VALUES (?, ?, ?)
                            ''', (facility_id, surface, count))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error inserting hotel {hotel_data['name']}: {str(e)}")
                conn.rollback()
                return False

    def process_json_file(self, filepath: str) -> int:
        """Process a single JSON file and return number of records processed"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                hotels = json.load(f)
            
            successful_inserts = 0
            for hotel in hotels:
                if self.insert_hotel_data(hotel):
                    successful_inserts += 1
                    
            logger.info(f"Processed {successful_inserts} hotels from {filepath}")
            return successful_inserts
            
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {str(e)}")
            return 0

    def consolidate_all_files(self):
        """Process all JSON files in the current directory"""
        json_files = [f for f in os.listdir() if f.endswith('.json')]
        total_hotels = 0
        
        for file in json_files:
            if 'checkpoint' not in file:  # Skip checkpoint files
                logger.info(f"Processing {file}...")
                total_hotels += self.process_json_file(file)
        
        logger.info(f"Completed consolidation. Total hotels in database: {total_hotels}")
        return total_hotels

def main():
    try:
        logger.info("Starting database consolidation process...")
        db = TennisHotelsDB()
        total_hotels = db.consolidate_all_files()
        logger.info(f"Successfully consolidated {total_hotels} hotels into the database")
    except Exception as e:
        logger.error(f"Error during consolidation process: {str(e)}")
        raise

if __name__ == "__main__":
    main() 