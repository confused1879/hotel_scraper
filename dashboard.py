import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from typing import Dict
#import folium
#from streamlit_folium import folium_static
import json
import os
from amadeus_hotels import AmadeusHotelSearch

class TennisHotelsDashboard:
    def __init__(self, db_path: str = 'tennis_hotels.db'):
        self.db_path = db_path
        self.load_data()
        self.amadeus_search = AmadeusHotelSearch()

    def load_data(self):
        """Load data from SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Load main hotel data with tennis facilities and geocoding
            self.df = pd.read_sql('''
                SELECT 
                    h.id as hotel_id,
                    h.name,
                    h.location,
                    h.country,
                    h.source_country,
                    h.star_rating,
                    h.rating_score,
                    h.rating_text,
                    h.page_number,
                    h.scrape_timestamp,
                    t.total_courts,
                    t.lighted_courts,
                    t.opening_hours,
                    t.court_cost,
                    t.lessons_available,
                    t.equipment_rental,
                    t.tennis_camps,
                    t.tournaments,
                    t.tennis_shop,
                    p.amount as price,
                    p.currency,
                    p.provider,
                    p.room_type,
                    g.latitude,
                    g.longitude,
                    g.country_code,
                    g.formatted_address
                FROM hotels h
                LEFT JOIN tennis_facilities t ON h.id = t.hotel_id
                LEFT JOIN prices p ON h.id = p.hotel_id
                LEFT JOIN geocoding g ON h.location = g.location_string
            ''', conn)
            
            # Load court surfaces
            surfaces_df = pd.read_sql('''
                SELECT 
                    h.id as hotel_id,
                    GROUP_CONCAT(cs.surface_type, '; ') as surface_types,
                    GROUP_CONCAT(cs.court_count, '; ') as court_counts
                FROM hotels h
                JOIN tennis_facilities t ON h.id = t.hotel_id
                LEFT JOIN court_surfaces cs ON t.id = cs.facility_id
                GROUP BY h.id
            ''', conn)
            
            # Merge surfaces into main dataframe
            self.df = self.df.merge(surfaces_df, on='hotel_id', how='left')
            
            # Clean and process data
            self.df['location'] = self.df['location'].fillna('')
            self.df['country'] = self.df['country'].fillna('')
            self.df['price'] = pd.to_numeric(self.df['price'], errors='coerce')
            self.df['total_courts'] = pd.to_numeric(self.df['total_courts'], errors='coerce')
            
            # Convert boolean columns
            bool_columns = ['lessons_available', 'equipment_rental', 'tennis_camps', 'tournaments', 'tennis_shop']
            for col in bool_columns:
                self.df[col] = self.df[col].fillna(False)
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            self.df = pd.DataFrame()

    def create_map(self, data):
        """Create a plotly map with hotel markers"""
        try:
            # Remove any rows with missing coordinates
            data = data.dropna(subset=['latitude', 'longitude'])
            
            if len(data) == 0:
                st.warning("No hotels with location data to display on map.")
                return None
            
            # Create hover text
            hover_text = data.apply(lambda row: f"""
                <b>{row['name']}</b><br>
                Location: {row['location']}, {row['country']}<br>
                Tennis Courts: {row['total_courts']} ({row['lighted_courts']} lighted)<br>
                Surfaces: {row['surface_types'] or 'Not specified'}<br>
                Price: {row['currency']} {row['price']:.2f}<br>
                Rating: {row['rating_score']} ({row['rating_text']})
            """, axis=1)

            # Create the map
            fig = px.scatter_mapbox(
                data,
                lat='latitude',
                lon='longitude',
                hover_name='name',
                hover_data={
                    'latitude': False,
                    'longitude': False,
                    'total_courts': True,
                    'rating_score': True,
                    'price': True
                },
                zoom=2,
                title='Hotel Locations'
            )

            # Update the layout to use OpenStreetMap style
            fig.update_layout(
                mapbox_style="open-street-map",
                margin={"r":0,"t":0,"l":0,"b":0},
                height=600
            )

            return fig
            
        except Exception as e:
            st.error(f"Error creating map: {str(e)}")
            return None

    def run_dashboard(self):
        st.title("Tennis Hotels Dashboard")
        
        # Statistics at the top
        st.subheader("Overall Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Hotels", len(self.df))
        with col2:
            st.metric("Average Courts", f"{self.df['total_courts'].mean():.1f}")
        with col3:
            st.metric("Average Rating", f"{self.df['rating_score'].mean():.1f}")
        
        # Create three tabs
        tab1, tab2, tab3 = st.tabs(["Tennis Hotels Database", "Tennis Courts Analysis", "Amadeus Hotel Search"])
        
        with tab1:
            self.show_tennis_hotels_tab()
        
        with tab2:
            self.show_tennis_courts_tab()
        
        with tab3:
            self.show_amadeus_search_tab()

    def show_amadeus_search_tab(self):
        """Display Amadeus hotel search interface"""
        st.subheader("Search Hotels via Amadeus")
        
        # City search
        city_query = st.text_input("Enter city name", "")
        if city_query:
            cities = self.amadeus_search.get_city_search(city_query)
            if cities:
                city_options = {f"{c['city_name']}, {c['country_code']}": c['city_code'] 
                              for c in cities}
                selected_city = st.selectbox("Select city", list(city_options.keys()))
                city_code = city_options[selected_city]
                
                # Date selection
                col1, col2 = st.columns(2)
                with col1:
                    check_in = st.date_input("Check-in date")
                with col2:
                    check_out = st.date_input("Check-out date")
                
                # Filters
                col3, col4 = st.columns(2)
                with col3:
                    ratings = st.multiselect(
                        "Hotel rating",
                        ['1', '2', '3', '4', '5'],
                        default=['4', '5']
                    )
                with col4:
                    adults = st.number_input("Number of adults", 1, 10, 2)
                
                # Price range
                price_min = st.number_input("Minimum price", 0)
                price_max = st.number_input("Maximum price", 1000)
                
                if st.button("Search Hotels"):
                    hotels_df = self.amadeus_search.search_hotels(
                        city_code=city_code,
                        check_in=check_in.strftime('%Y-%m-%d'),
                        check_out=check_out.strftime('%Y-%m-%d'),
                        adults=adults,
                        ratings=ratings,
                        price_range={'min': price_min, 'max': price_max}
                    )
                    
                    if not hotels_df.empty:
                        # Show results on map
                        st.subheader("Hotel Locations")
                        map_fig = self.create_map(hotels_df)
                        if map_fig:
                            st.plotly_chart(map_fig, use_container_width=True)
                        
                        # Show results table
                        st.subheader("Hotel List")
                        st.dataframe(hotels_df[[
                            'name', 'rating', 'price_total', 'currency',
                            'address', 'chain_code'
                        ]])
                    else:
                        st.warning("No hotels found matching your criteria")
            else:
                st.warning("No cities found matching your search")

    def show_tennis_hotels_tab(self):
        """Show original tennis hotels dashboard content"""
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Price range filter
        if not self.df.empty and 'price' in self.df.columns:
            valid_prices = self.df['price'].dropna()
            if not valid_prices.empty:
                price_range = st.sidebar.slider(
                    'Price Range',
                    float(valid_prices.min()),
                    float(valid_prices.max()),
                    (float(valid_prices.min()), float(valid_prices.max()))
                )
            else:
                price_range = (0, 0)
        
        # Courts filter
        min_courts = st.sidebar.number_input('Minimum Number of Courts', 0)
        
        # Amenities filters
        st.sidebar.subheader("Amenities")
        show_lessons = st.sidebar.checkbox("Tennis Lessons Available")
        show_equipment = st.sidebar.checkbox("Equipment Rental")
        show_camps = st.sidebar.checkbox("Tennis Camps")
        
        # Filter data
        filtered_df = self.df.copy()
        filtered_df = filtered_df[
            (filtered_df['price'] >= price_range[0]) &
            (filtered_df['price'] <= price_range[1]) &
            (filtered_df['total_courts'] >= min_courts)
        ]
        
        if show_lessons:
            filtered_df = filtered_df[filtered_df['lessons_available'] == True]
        if show_equipment:
            filtered_df = filtered_df[filtered_df['equipment_rental'] == True]
        if show_camps:
            filtered_df = filtered_df[filtered_df['tennis_camps'] == True]
        
        # Main content - just use the full width for the map
        st.subheader("Hotel Locations")
        map_fig = self.create_map(filtered_df)
        if map_fig:
            st.plotly_chart(map_fig, use_container_width=True)
        
        # Analysis section
        st.subheader("Analysis")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Courts distribution
            fig_courts = px.histogram(
                filtered_df,
                x='total_courts',
                title='Distribution of Tennis Courts',
                labels={'total_courts': 'Number of Courts', 'count': 'Number of Hotels'}
            )
            st.plotly_chart(fig_courts)
        
        with col4:
            # Price vs Rating scatter
            fig_price = px.scatter(
                filtered_df,
                x='rating_score',
                y='price',
                color='total_courts',
                hover_data=['name', 'location'],
                title='Price vs Rating (color = number of courts)',
                labels={'rating_score': 'Rating', 'price': 'Price', 'total_courts': 'Number of Courts'}
            )
            st.plotly_chart(fig_price)
        
        # Detailed hotel list
        st.subheader("Hotel Details")
        if st.checkbox("Show detailed hotel list"):
            display_cols = [
                'name', 'location', 'country', 'total_courts', 'lighted_courts',
                'surface_types', 'price', 'currency', 'rating_score', 'rating_text'
            ]
            st.dataframe(filtered_df[display_cols])

    def show_tennis_courts_tab(self):
        """Show tennis courts analysis content"""
        # Use the same filters as the main tab
        st.sidebar.header("Filters")
        
        # Courts filter
        min_courts = st.sidebar.number_input('Minimum Number of Courts', 0, key='courts_tennis')
        
        # Filter data
        filtered_df = self.df.copy()
        filtered_df = filtered_df[filtered_df['total_courts'] >= min_courts]
        
        # Hotel selector
        selected_hotel = st.selectbox(
            "Select a hotel to view tennis court details",
            filtered_df['name'].tolist(),
            format_func=lambda x: f"{x} ({filtered_df[filtered_df['name']==x]['location'].iloc[0]}, {filtered_df[filtered_df['name']==x]['country'].iloc[0]})"
        )
        
        if selected_hotel:
            hotel_data = filtered_df[filtered_df['name'] == selected_hotel].iloc[0]
            
            # Create two columns for tennis-specific visualizations
            court_col1, court_col2 = st.columns(2)
            
            with court_col1:
                # Create metrics for court numbers
                st.metric("Total Courts", int(hotel_data['total_courts']))
                st.metric("Lighted Courts", int(hotel_data['lighted_courts']))
                
                # Show court cost and hours
                st.subheader("Court Information")
                st.write(f"**Opening Hours:** {hotel_data['opening_hours'] or 'Not specified'}")
                st.write(f"**Court Cost:** {hotel_data['court_cost'] or 'Not specified'}")
                
                # Show amenities
                st.subheader("Tennis Amenities")
                amenities = {
                    "Tennis Lessons": hotel_data['lessons_available'],
                    "Equipment Rental": hotel_data['equipment_rental'],
                    "Tennis Camps": hotel_data['tennis_camps'],
                    "Tournaments": hotel_data['tournaments'],
                    "Tennis Shop": hotel_data['tennis_shop']
                }
                for amenity, available in amenities.items():
                    st.write(f"{'✓' if available else '✗'} {amenity}")
            
            with court_col2:
                # Create pie chart of court surfaces
                if pd.notna(hotel_data['surface_types']) and pd.notna(hotel_data['court_counts']):
                    surfaces = hotel_data['surface_types'].split('; ')
                    counts = [int(count) for count in hotel_data['court_counts'].split('; ')]
                    
                    surface_df = pd.DataFrame({
                        'Surface': surfaces,
                        'Count': counts
                    })
                    
                    fig_surfaces = px.pie(
                        surface_df,
                        values='Count',
                        names='Surface',
                        title='Court Surface Distribution'
                    )
                    st.plotly_chart(fig_surfaces)
                    
                    # Show surface details table
                    st.subheader("Surface Details")
                    surface_df['Percentage'] = (surface_df['Count'] / surface_df['Count'].sum() * 100).round(1)
                    surface_df['Percentage'] = surface_df['Percentage'].astype(str) + '%'
                    st.dataframe(surface_df, use_container_width=True)
                else:
                    st.write("No surface type information available")

def main():
    dashboard = TennisHotelsDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main() 