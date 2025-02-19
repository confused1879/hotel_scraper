import streamlit as st
from amadeus_hotels import AmadeusHotelSearch
from datetime import datetime, timedelta

def test_search():
    st.title("Amadeus API Test")
    
    # Initialize the search
    search = AmadeusHotelSearch()
    
    # Test city search
    st.write("Testing city search for 'PAR'...")  # Using Paris as an example
    cities = search.get_city_search("PAR")
    if cities:
        st.write(f"Found {len(cities)} cities:")
        for city in cities:
            st.write(f"- {city['city_name']}, {city['country_code']} ({city['city_code']})")
        
        # Test hotel search using first city
        city_code = cities[0]['city_code']
        st.write(f"\nTesting hotel search in {cities[0]['city_name']}...")
        
        # Set dates for 30 days from now
        check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        check_out = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d')
        
        st.write(f"Check-in: {check_in}")
        st.write(f"Check-out: {check_out}")
        
        # Simple search with minimal parameters
        hotels_df = search.search_hotels(
            city_code=city_code,
            check_in=check_in,
            check_out=check_out,
            adults=2
        )
        
        if not hotels_df.empty:
            st.write(f"\nFound {len(hotels_df)} hotels. First 5 hotels:")
            st.dataframe(hotels_df[[
                'name', 'rating', 'price_total', 'currency',
                'room_type', 'board_type'
            ]].head())
        else:
            st.error("No hotels found")
    else:
        st.error("No cities found")

if __name__ == "__main__":
    test_search() 