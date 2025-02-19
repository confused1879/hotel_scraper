import sqlite3
import json
import logging
import time
from typing import Dict, Optional, Tuple
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GeocodingUpdater:
    def __init__(self, db_path: str = 'tennis_hotels.db'):
        self.db_path = db_path
        self.cache_file = 'geocode_cache.json'
        self.setup_geocoding_table()
        self.load_cache()

    def setup_geocoding_table(self):
        """Create geocoding table if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS geocoding (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_string TEXT UNIQUE,
                    latitude REAL,
                    longitude REAL,
                    country_code TEXT,
                    formatted_address TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def load_cache(self):
        """Load existing geocoding cache from file"""
        self.cache = {}
        if Path(self.cache_file).exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached locations")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")

    def save_cache(self):
        """Save geocoding cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Saved {len(self.cache)} locations to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def geocode_location(self, location: str, country: str = '') -> Optional[Dict]:
        """
        Geocode a location using Nominatim API
        Returns dict with lat, lon, and other location data
        """
        if not location:
            return None

        # Check cache first
        cache_key = f"{location}, {country}".strip(', ')
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Construct search query
        search_query = location
        if country:
            search_query = f"{location}, {country}"

        # Call Nominatim API
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': search_query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'TennisHotelResearch/1.0'
            }

            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

            if results:
                result = results[0]
                geocoded_data = {
                    'lat': float(result['lat']),
                    'lon': float(result['lon']),
                    'country_code': result.get('address', {}).get('country_code', ''),
                    'formatted_address': result.get('display_name', '')
                }
                
                # Cache the result
                self.cache[cache_key] = geocoded_data
                self.save_cache()
                
                # Respect API usage limits
                time.sleep(1)
                
                return geocoded_data

        except Exception as e:
            logger.error(f"Geocoding error for {search_query}: {e}")

        return None

    def update_database_geocoding(self):
        """Update database with geocoding information and country for all hotels"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all unique locations that need geocoding
            cursor.execute('''
                SELECT DISTINCT h.location, h.country 
                FROM hotels h 
                LEFT JOIN geocoding g ON h.location = g.location_string
                WHERE g.location_string IS NULL
                AND h.location IS NOT NULL
            ''')
            
            locations_to_geocode = cursor.fetchall()
            logger.info(f"Found {len(locations_to_geocode)} locations to geocode")

            for location, country in locations_to_geocode:
                geocoded = self.geocode_location(location, country)
                if geocoded:
                    try:
                        # Insert geocoding data
                        cursor.execute('''
                            INSERT OR REPLACE INTO geocoding 
                            (location_string, latitude, longitude, country_code, formatted_address)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            location,
                            geocoded['lat'],
                            geocoded['lon'],
                            geocoded['country_code'],
                            geocoded['formatted_address']
                        ))
                        
                        # Extract country from formatted address
                        country_name = geocoded['formatted_address'].split(', ')[-1]
                        
                        # Update country in hotels table
                        cursor.execute('''
                            UPDATE hotels 
                            SET country = ? 
                            WHERE location = ? AND (country IS NULL OR country = '')
                        ''', (country_name, location))
                        
                        conn.commit()
                        logger.info(f"Added geocoding and updated country for {location} to {country_name}")
                    except Exception as e:
                        logger.error(f"Error updating data for {location}: {e}")

    def verify_geocoding(self) -> Tuple[int, int, int]:
        """Verify geocoding and country coverage"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total locations, geocoded locations, and country coverage
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT h.location) as total_locations,
                    COUNT(DISTINCT g.location_string) as geocoded_locations,
                    COUNT(DISTINCT CASE WHEN h.country IS NOT NULL AND h.country != '' 
                                      THEN h.location END) as locations_with_country
                FROM hotels h
                LEFT JOIN geocoding g ON h.location = g.location_string
                WHERE h.location IS NOT NULL
            ''')
            
            total, geocoded, with_country = cursor.fetchone()
            geo_coverage = (geocoded / total * 100) if total > 0 else 0
            country_coverage = (with_country / total * 100) if total > 0 else 0
            
            logger.info(f"Geocoding coverage: {geocoded}/{total} locations ({geo_coverage:.1f}%)")
            logger.info(f"Country coverage: {with_country}/{total} locations ({country_coverage:.1f}%)")
            return total, geocoded, with_country

    def update_missing_countries(self):
        """Update missing countries using existing geocoding data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all locations with empty countries but have geocoding
            cursor.execute('''
                SELECT h.location, g.formatted_address 
                FROM hotels h
                JOIN geocoding g ON h.location = g.location_string
                WHERE (h.country IS NULL OR h.country = '')
            ''')
            
            locations_to_update = cursor.fetchall()
            logger.info(f"Found {len(locations_to_update)} locations needing country updates")

            for location, formatted_address in locations_to_update:
                try:
                    # Extract country from formatted address
                    country_name = formatted_address.split(', ')[-1]
                    
                    # Update country in hotels table
                    cursor.execute('''
                        UPDATE hotels 
                        SET country = ? 
                        WHERE location = ?
                    ''', (country_name, location))
                    
                    conn.commit()
                    logger.info(f"Updated country for {location} to {country_name}")
                except Exception as e:
                    logger.error(f"Error updating country for {location}: {e}")

def main():
    updater = GeocodingUpdater()
    
    # Check initial coverage
    logger.info("Initial coverage:")
    initial_total, initial_geocoded, initial_countries = updater.verify_geocoding()
    
    # First update geocoding
    updater.update_database_geocoding()
    
    # Then update missing countries using existing geocoding data
    logger.info("\nUpdating missing countries...")
    updater.update_missing_countries()
    
    # Check final coverage
    logger.info("\nFinal coverage:")
    final_total, final_geocoded, final_countries = updater.verify_geocoding()
    
    # Report results
    new_geocoded = final_geocoded - initial_geocoded
    new_countries = final_countries - initial_countries
    logger.info(f"\nNewly geocoded locations: {new_geocoded}")
    logger.info(f"Newly added countries: {new_countries}")

if __name__ == "__main__":
    main() 