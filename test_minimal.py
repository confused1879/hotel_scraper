import streamlit as st
from amadeus import Client, ResponseError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_minimal():
    try:
        amadeus = Client(
            client_id=st.secrets["AMADEUS_API_KEY"],
            client_secret=st.secrets["AMADEUS_API_SECRET"],
            hostname='test'
        )
        
        # Search for hotels in Paris with tennis facilities
        print("\nSearching for hotels with tennis facilities in Paris...")
        hotels_response = amadeus.reference_data.locations.hotels.by_city.get(
            cityCode='PAR',
            amenities=['TENNIS'],  # From the amenities enum in the documentation
            radius=50,             # Search within 50 units
            radiusUnit='KM',       # Radius in kilometers
            hotelSource='ALL'      # Search both BEDBANK and DIRECTCHAIN
        )
        
        if hotels_response.data:
            print(f"\nFound {len(hotels_response.data)} hotels with tennis facilities")
            print("\nHotel Details:")
            for hotel in hotels_response.data:
                print(f"\nName: {hotel['name']}")
                print(f"Hotel ID: {hotel['hotelId']}")
                print(f"Chain Code: {hotel.get('chainCode', 'N/A')}")
                if 'geoCode' in hotel:
                    print(f"Location: {hotel['geoCode'].get('latitude', 'N/A')}, {hotel['geoCode'].get('longitude', 'N/A')}")
                if 'address' in hotel:
                    print(f"Country: {hotel['address'].get('countryCode', 'N/A')}")
                print("-" * 50)
        else:
            print("No hotels found with tennis facilities")
                
    except ResponseError as error:
        print(f"Error code: {error.code}")
        print(f"Error message: {str(error)}")
        print(f"Full response: {error.response.body}")
        if hasattr(error, 'description'):
            print(f"Error description: {error.description}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    test_minimal()