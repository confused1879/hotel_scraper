import streamlit as st
from amadeus import Client, ResponseError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_hotel_ids():
    try:
        amadeus = Client(
            client_id=st.secrets["AMADEUS_API_KEY"],
            client_secret=st.secrets["AMADEUS_API_SECRET"],
            hostname='test'
        )
        
        # Try getting hotels in different cities
        for city in ['PAR', 'LON', 'NYC']:
            print(f"\nTesting city: {city}")
            hotels_response = amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=city
            )
            
            if hotels_response.data:
                print(f"Found {len(hotels_response.data)} hotels")
                # Print first 5 hotels with more details
                for hotel in hotels_response.data[:5]:
                    print(f"\nHotel ID: {hotel['hotelId']}")
                    print(f"Name: {hotel.get('name', 'N/A')}")
                    print(f"Chain Code: {hotel.get('chainCode', 'N/A')}")
                    print(f"GDS Code: {hotel.get('gdsCode', 'N/A')}")
                    # Print raw hotel data for inspection
                    print("Raw data:", hotel)
            
    except ResponseError as error:
        print(f"Error code: {error.code}")
        print(f"Error message: {str(error)}")
        print(f"Full response: {error.response.body}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    test_hotel_ids() 