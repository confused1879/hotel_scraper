import os
from dotenv import load_dotenv
from amadeus import Client, ResponseError
from typing import Dict, List, Optional
import logging
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AmadeusHotelSearch:
    def __init__(self):
        try:
            # Initialize Amadeus client with credentials from Streamlit secrets
            self.amadeus = Client(
                client_id=st.secrets["AMADEUS_API_KEY"],
                client_secret=st.secrets["AMADEUS_API_SECRET"],
                hostname='test'
            )
            logger.info("Initialized Amadeus client in test environment")
        except Exception as e:
            logger.error(f"Failed to initialize Amadeus client: {str(e)}")
            st.error("Failed to initialize Amadeus API. Please check your credentials.")
            self.amadeus = None

    def search_hotels(self, 
                     city_code: str,
                     adults: int = 2,
                     check_in: Optional[str] = None,
                     check_out: Optional[str] = None) -> pd.DataFrame:
        """Search hotels using Amadeus API"""
        if not self.amadeus:
            st.error("Amadeus API not initialized")
            return pd.DataFrame()

        try:
            # Get hotels in city using the reference data endpoint
            logger.info(f"Searching hotels in {city_code}")
            hotels_response = self.amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=city_code
            )

            if not hotels_response.data:
                logger.warning(f"No hotels found in {city_code}")
                return pd.DataFrame()

            logger.info(f"Found {len(hotels_response.data)} hotels")

            # Process each hotel
            all_hotels_data = []
            for hotel in hotels_response.data[:20]:  # Limit to first 20 hotels
                hotel_info = {
                    'hotel_id': hotel['hotelId'],
                    'name': hotel['name'],
                    'chain_code': hotel.get('chainCode', ''),
                    'iata_code': hotel.get('iataCode', ''),
                    'latitude': float(hotel.get('geoCode', {}).get('latitude', 0)),
                    'longitude': float(hotel.get('geoCode', {}).get('longitude', 0)),
                    'address': hotel.get('address', {}).get('lines', [''])[0],
                    'city_code': hotel.get('cityCode', ''),
                    'country_code': hotel.get('address', {}).get('countryCode', '')
                }
                all_hotels_data.append(hotel_info)

            return pd.DataFrame(all_hotels_data)

        except ResponseError as error:
            logger.error(f"Amadeus API error: {error}")
            logger.error(f"Error response: {error.response.body}")
            st.error(f"API Error: {str(error)}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error searching hotels: {str(e)}")
            st.error(f"Error: {str(e)}")
            return pd.DataFrame()

    def get_city_search(self, keyword: str) -> List[Dict]:
        """Search for city codes based on keyword"""
        if not self.amadeus:
            st.error("Amadeus API not initialized")
            return []
            
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=keyword,
                subType='CITY'
            )
            
            return [{
                'city_code': location['iataCode'],
                'city_name': location['name'],
                'country_code': location['address'].get('countryCode', ''),
                'state_code': location['address'].get('stateCode', '')
            } for location in response.data]
            
        except ResponseError as error:
            logger.error(f"Amadeus API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Error searching cities: {str(e)}")
            return []

    def get_hotel_offers(self, 
                        hotel_id: str,
                        check_in: Optional[str] = None,
                        check_out: Optional[str] = None,
                        adults: int = 1,
                        rooms: int = 1) -> pd.DataFrame:
        """Get offers for a specific hotel"""
        if not self.amadeus:
            st.error("Amadeus API not initialized")
            return pd.DataFrame()

        try:
            # Set default dates if not provided
            if not check_in or not check_out:
                tomorrow = datetime.now() + timedelta(days=1)
                day_after = tomorrow + timedelta(days=1)
                check_in = tomorrow.strftime('%Y-%m-%d')
                check_out = day_after.strftime('%Y-%m-%d')

            logger.info(f"Getting offers for hotel {hotel_id} from {check_in} to {check_out}")
            
            response = self.amadeus.shopping.hotel_offers.get(
                hotelIds=hotel_id,
                checkInDate=check_in,
                checkOutDate=check_out,
                adults=adults,
                roomQuantity=rooms
            )

            if not response.data:
                logger.warning(f"No offers found for hotel {hotel_id}")
                return pd.DataFrame()

            # Process offers into DataFrame
            offers_data = []
            for offer in response.data:
                hotel = offer['hotel']
                for room_offer in offer.get('offers', []):
                    offer_info = {
                        'hotel_id': hotel['hotelId'],
                        'hotel_name': hotel['name'],
                        'room_type': room_offer.get('room', {}).get('type', ''),
                        'board_type': room_offer.get('boardType', ''),
                        'price': float(room_offer.get('price', {}).get('total', 0)),
                        'currency': room_offer.get('price', {}).get('currency', ''),
                        'check_in': check_in,
                        'check_out': check_out,
                        'adults': adults,
                        'rooms': rooms,
                        'cancellation_policy': room_offer.get('policies', {}).get('cancellation', {}).get('description', ''),
                        'offer_id': room_offer.get('id', '')
                    }
                    offers_data.append(offer_info)

            return pd.DataFrame(offers_data)

        except ResponseError as error:
            logger.error(f"Amadeus API error: {error}")
            logger.error(f"Error response: {error.response.body}")
            st.error(f"API Error: {str(error)}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error getting hotel offers: {str(e)}")
            st.error(f"Error: {str(e)}")
            return pd.DataFrame()

def main():
    # Example usage
    search = AmadeusHotelSearch()
    
    # Search for a city
    cities = search.get_city_search("London")
    if cities:
        city_code = cities[0]['city_code']
        
        # Search for hotels
        hotels_df = search.search_hotels(
            city_code=city_code,
            ratings=['4', '5'],
            price_range={'min': 100, 'max': 500}
        )
        
        print(f"Found {len(hotels_df)} hotels in {cities[0]['city_name']}")
        print(hotels_df.head())

if __name__ == "__main__":
    main() 