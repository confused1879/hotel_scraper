import streamlit as st
from amadeus import Client, ResponseError

def test_credentials():
    try:
        # Initialize client with credentials
        amadeus = Client(
            client_id=st.secrets["AMADEUS_API_KEY"],
            client_secret=st.secrets["AMADEUS_API_SECRET"]
        )
        
        # Test a simple API call
        response = amadeus.reference_data.locations.get(
            keyword='LON',
            subType='CITY'
        )
        
        print("API credentials are working!")
        print("Sample response:", response.data[0])
        return True
        
    except ResponseError as error:
        print(f"API Error: {error}")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_credentials() 