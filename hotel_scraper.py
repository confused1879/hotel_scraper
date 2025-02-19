from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import logging
from typing import Dict, List, Optional
import re
import random
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TravelmythScraper:
    def __init__(self):
        self.base_url = "https://www.travelmyth.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Add delay configuration
        self.delay_config = {
            "min_delay": 3,  # Minimum delay in seconds
            "max_delay": 7,  # Maximum delay in seconds
            "page_load_delay": (1, 3),  # Random delay after page load
            "hotel_process_delay": (0.5, 1.5)  # Random delay between processing hotels
        }

        # Add European countries list
        self.european_countries = [
            "Albania", "Andorra", "Austria", "Belarus", "Belgium", "Bosnia-Herzegovina",
            "Bulgaria", "Croatia", "Cyprus", "Czech-Republic", "Denmark", "Estonia",
            "Finland", "France", "Germany", "Greece", "Hungary", "Iceland", "Ireland",
            "Italy", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta",
            "Moldova", "Monaco", "Montenegro", "Netherlands", "North-Macedonia", "Norway",
            "Poland", "Portugal", "Romania", "Russia", "San-Marino", "Serbia", "Slovakia",
            "Slovenia", "Spain", "Sweden", "Switzerland", "Ukraine", "United-Kingdom", "Vatican-City"
        ]

        self.european_countries = [
            #"Portugal", "Spain", "United-Kingdom"
            "World", "Portugal"
        ]

    def random_delay(self, min_seconds: float, max_seconds: float):
        """Add a random delay between operations"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)

    def extract_hotel_data(self, hotel_element) -> Dict:
        """Extract data from a single hotel element with improved handling"""
        try:
            logger.debug("Starting data extraction for hotel element")
            
            # Initialize hotel data structure
            hotel_data = {
                "name": "",
                "location": "",
                "country": "",
                "source_country": self.european_countries[0],  # Set source_country at initialization
                "star_rating": 0,
                "rating_score": None,
                "rating_text": "",
                "price": {
                    "amount": None,
                    "currency": "USD",
                    "provider": "",
                    "room_type": "",
                    "cancellation_policy": ""
                },
                "tennis_facilities": {
                    "total_courts": 0,
                    "lighted_courts": 0,
                    "court_surfaces": [],
                    "surface_counts": {},
                    "opening_hours": "",
                    "court_cost": "",
                    "lessons_available": False,
                    "lessons_cost": "",
                    "equipment_rental": False,
                    "equipment_cost": "",
                    "requirements": [],
                    "tennis_camps": False,
                    "tournaments": False,
                    "tennis_shop": False,
                    "additional_info": []
                },
                "scrape_timestamp": datetime.now().isoformat()
            }

            # Extract hotel name with debug info
            name_element = hotel_element.query_selector(".hotel_li_name_link")
            if name_element:
                hotel_data["name"] = name_element.inner_text().strip()
                logger.debug(f"Found hotel name: {hotel_data['name']}")
            else:
                logger.warning("Could not find hotel name element")

            # Extract location and country
            location_element = hotel_element.query_selector(".hotel_property_type_location")
            if location_element:
                location_text = location_element.inner_text().strip()
                logger.debug(f"Raw location text: {location_text}")
                
                # Define all possible property type prefixes
                prefixes_to_remove = [
                    "Hotel in",
                    "Resort in",
                    "Guest House in",
                    "Bed & Breakfast in",
                    "Country House in",
                    "Hostel in",
                    "Apartment in",
                    "Aparthotel in",
                    "Villa in"
                ]
                
                # Clean up the location text
                location = location_text
                for prefix in prefixes_to_remove:
                    if location.startswith(prefix):
                        location = location.replace(prefix, "").strip()
                        break
                
                # Remove "Show on Map" and clean up whitespace
                location = location.split("Show on Map")[0].strip()
                
                # Split by newlines and get parts
                parts = [part.strip() for part in location.split('\n') if part.strip()]
                if parts:
                    # First part is location (city)
                    hotel_data["location"] = parts[0].rstrip(',')  # Remove trailing comma
                    
                    # Second part should be country
                    if len(parts) > 1:
                        hotel_data["country"] = parts[1]
                    else:
                        hotel_data["country"] = ""  # Default to empty if not found
                        
                    logger.debug(f"Extracted location: {hotel_data['location']}, country: {hotel_data['country']}")
                else:
                    logger.warning(f"Could not parse location from: {location_text}")

            # Extract star rating
            star_elements = hotel_element.query_selector_all(".fa-star.star_ratings")
            hotel_data["star_rating"] = len(star_elements)

            # Extract rating score and text
            rating_score = hotel_element.query_selector(".circle_rating")
            rating_text = hotel_element.query_selector(".rating_text")
            if rating_score:
                hotel_data["rating_score"] = float(rating_score.inner_text().strip())
            if rating_text:
                hotel_data["rating_text"] = rating_text.inner_text().strip()

            # Extract price information
            price_element = hotel_element.query_selector(".main_price_box")
            if price_element:
                price_amount = price_element.query_selector("div[style*='color:#B12704']")
                provider = price_element.query_selector("img[src*='provider_logos']")
                room_type = price_element.query_selector(".main_price_room_type")
                cancellation = price_element.query_selector(".cancellation_text")
                
                if price_amount:
                    price_text = price_amount.inner_text().strip()
                    # Handle different currency symbols
                    price_text = price_text.replace("£", "").replace("$", "").replace("€", "").replace(",", "")
                    try:
                        hotel_data["price"]["amount"] = float(price_text)
                        hotel_data["price"]["currency"] = "GBP"  # Set to GBP since we're using British pounds
                    except ValueError as e:
                        logger.warning(f"Could not parse price '{price_text}': {str(e)}")
                        hotel_data["price"]["amount"] = None
                if provider:
                    provider_src = provider.get_attribute("src")
                    hotel_data["price"]["provider"] = provider_src.split("/")[-1].replace(".png", "")
                if room_type:
                    hotel_data["price"]["room_type"] = room_type.inner_text().strip()
                if cancellation:
                    hotel_data["price"]["cancellation_policy"] = cancellation.inner_text().strip()

            # Find and expand the tennis section
            tennis_section = hotel_element.query_selector(".tab-height")
            if tennis_section:
                logger.debug("Found tennis section")
                
                # Click any "Show more" buttons
                show_more_buttons = tennis_section.query_selector_all("button.show_more_hotel_info")
                for button in show_more_buttons:
                    try:
                        button.click()
                        # Wait for content to load
                        time.sleep(0.5)
                        logger.debug("Clicked 'Show more' button")
                    except Exception as e:
                        logger.warning(f"Failed to click 'Show more' button: {e}")

                # Click any expand arrows
                expand_arrows = tennis_section.query_selector_all(".fa-chevron-down")
                for arrow in expand_arrows:
                    try:
                        arrow.click()
                        time.sleep(0.5)
                        logger.debug("Clicked expand arrow")
                    except Exception as e:
                        logger.warning(f"Failed to click expand arrow: {e}")

                # Get all tennis info divs
                questionnaire_divs = tennis_section.query_selector_all("div.tabs_content_font")
                for div in questionnaire_divs:
                    try:
                        # Get both label and value spans
                        spans = div.query_selector_all("span")
                        if len(spans) < 2:
                            continue

                        label_text = spans[0].inner_text().strip()
                        value_text = spans[1].inner_text().strip()
                        
                        logger.debug(f"Processing field: {label_text} = {value_text}")

                        # Improved field matching with flexible text comparison
                        if any(court_text in label_text.lower() for court_text in ["number of all tennis courts", "tennis courts total"]):
                            try:
                                count = int(''.join(filter(str.isdigit, value_text)))
                                hotel_data['tennis_facilities']['total_courts'] = count
                                logger.debug(f"Found total courts: {count}")
                            except ValueError:
                                logger.warning(f"Could not parse total courts from: {value_text}")

                        elif "lighted" in label_text.lower() and "court" in label_text.lower():
                            try:
                                count = int(''.join(filter(str.isdigit, value_text)))
                                hotel_data['tennis_facilities']['lighted_courts'] = count
                                logger.debug(f"Found lighted courts: {count}")
                            except ValueError:
                                logger.warning(f"Could not parse lighted courts from: {value_text}")

                        elif "terrain" in label_text.lower() or "surface" in label_text.lower():
                            # Get all surface divs
                            surface_divs = div.query_selector_all("div:has(svg)")
                            for surface_div in surface_divs:
                                surface_text = surface_div.inner_text().strip()
                                # Improved surface parsing
                                parts = surface_text.split("Number of courts:")
                                if len(parts) == 2:
                                    surface_type = parts[0].strip()
                                    try:
                                        count = int(''.join(filter(str.isdigit, parts[1])))
                                        if surface_type not in hotel_data['tennis_facilities']['court_surfaces']:
                                            hotel_data['tennis_facilities']['court_surfaces'].append(surface_type)
                                        hotel_data['tennis_facilities']['surface_counts'][surface_type] = count
                                        logger.debug(f"Found surface: {surface_type} with {count} courts")
                                    except ValueError:
                                        logger.warning(f"Could not parse court count for surface: {surface_type}")

                        elif "opening hours" in label_text.lower():
                            hotel_data['tennis_facilities']['opening_hours'] = value_text
                            logger.debug(f"Found opening hours: {value_text}")

                        elif "cost" in label_text.lower() and "court" in label_text.lower():
                            hotel_data['tennis_facilities']['court_cost'] = value_text
                            logger.debug(f"Found court cost: {value_text}")

                        elif "tennis lessons" in label_text.lower():
                            # Improved lessons parsing
                            hotel_data['tennis_facilities']['lessons_available'] = not any(
                                no_text in value_text.lower() 
                                for no_text in ['no', 'νο', 'нет']
                            )
                            if "charge" in value_text.lower() or "cost" in value_text.lower():
                                cost_parts = value_text.split(":")
                                if len(cost_parts) > 1:
                                    hotel_data['tennis_facilities']['lessons_cost'] = cost_parts[1].strip()
                            logger.debug(f"Found lessons info: {value_text}")

                    except Exception as e:
                        logger.warning(f"Error processing tennis info div: {e}")
                        continue

            logger.debug("Completed data extraction for hotel")
            return hotel_data

        except Exception as e:
            logger.error(f"Error extracting hotel data: {str(e)}")
            return None

    def get_total_pages(self, page) -> int:
        """Extract total number of pages from pagination"""
        try:
            # Get all page numbers from the pagination
            page_links = page.query_selector_all(".pagination .page-link")
            if page_links:
                page_numbers = []
                for link in page_links:
                    title = link.get_attribute("title")
                    if title and title.isdigit():  # Only get numeric page numbers
                        page_numbers.append(int(title))
                
                total_pages = max(page_numbers) if page_numbers else 1
                logger.info(f"Found {total_pages} total pages")
                return total_pages
                
            return 1
        except Exception as e:
            logger.error(f"Error getting total pages: {str(e)}")
            return 1

    def navigate_to_next_page(self, page, current_page: int) -> bool:
        """Navigate to the next page and return success status"""
        try:
            # Find the next button using the correct title (current_page + 1)
            next_button = page.query_selector(f"li.page-item span.page-link[title='{current_page + 1}']")
            if next_button:
                next_button.click()
                logger.info(f"Clicked next page button (page {current_page + 1})")
                
                # Wait for the page load
                page.wait_for_load_state("networkidle")
                
                # Wait for hotels to load on new page
                page.wait_for_selector(".hotel_repeat", timeout=30000)
                
                # Verify we're on the new page by checking URL
                current_url = page.url
                if f"page={current_page + 1}" in current_url:
                    logger.info(f"Successfully navigated to page {current_page + 1}")
                    return True
                else:
                    logger.error(f"Failed to navigate - URL doesn't contain correct page number")
                    return False
            else:
                logger.info(f"Next page button (page {current_page + 1}) not found")
                return False
            
        except Exception as e:
            logger.error(f"Error navigating to next page: {str(e)}")
            return False

    def save_checkpoint(self, data: List[Dict], current_page: int):
        """Save checkpoint after each page"""
        try:
            # Save the current data to a checkpoint file
            checkpoint_file = f'tennis_hotels_checkpoint_page_{current_page}.json'
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Checkpoint saved for page {current_page}")
            
            # Also update the main file with all data so far
            with open('tennis_hotels.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Main data file updated with {len(data)} hotels")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {str(e)}")

    def scrape_hotels(self, base_url: str) -> List[Dict]:
        """Main scraping function with pagination support"""
        all_hotels_data = []
        current_page = 1

        try:
            logger.info(f"Starting browser session...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.headers["User-Agent"]
                )
                page = context.new_page()

                while True:
                    # Add random delay before requesting new page
                    self.random_delay(self.delay_config["min_delay"], self.delay_config["max_delay"])
                    
                    # Construct URL with page parameter
                    url = f"{base_url}&page={current_page}" if current_page > 1 else base_url
                    logger.info(f"Scraping page {current_page}, URL: {url}")
                    
                    # Navigate to page
                    response = page.goto(url, wait_until="networkidle")
                    logger.info(f"Page {current_page} response status: {response.status}")
                    
                    # Random delay after page load
                    self.random_delay(*self.delay_config["page_load_delay"])
                    
                    # Get total pages on first iteration
                    if current_page == 1:
                        total_pages = self.get_total_pages(page)
                        logger.info(f"Total pages to scrape: {total_pages}")

                    # Wait for hotels to load
                    logger.info(f"Waiting for hotel elements on page {current_page}...")
                    try:
                        logger.debug("Trying selector: .hotel_repeat")
                        page.wait_for_selector(".hotel_repeat", timeout=30000)
                    except Exception as e:
                        logger.error(f"Failed to load hotels on page {current_page}: {str(e)}")
                        break

                    # Get all hotel elements
                    hotel_elements = page.query_selector_all(".hotel_repeat")
                    logger.info(f"Found {len(hotel_elements)} hotels on page {current_page}")

                    page_hotels_data = []  # Store hotels from current page

                    # Extract data from each hotel
                    for index, hotel_element in enumerate(hotel_elements, 1):
                        # Add random delay between processing hotels
                        self.random_delay(*self.delay_config["hotel_process_delay"])
                        
                        logger.info(f"Processing hotel {index}/{len(hotel_elements)} on page {current_page}")
                        hotel_data = self.extract_hotel_data(hotel_element)
                        if hotel_data:
                            # Add page number to hotel data for tracking
                            hotel_data['page_number'] = current_page
                            page_hotels_data.append(hotel_data)
                            logger.debug(f"Successfully extracted data for hotel: {hotel_data['name']}")
                        else:
                            logger.warning(f"Failed to extract data for hotel #{index} on page {current_page}")

                    # Add page data to all data
                    all_hotels_data.extend(page_hotels_data)
                    
                    # Save checkpoint after each page
                    self.save_checkpoint(all_hotels_data, current_page)

                    # Check if we should continue to next page
                    if current_page >= total_pages:
                        logger.info("Reached last page")
                        break

                    # Navigate to next page
                    if self.navigate_to_next_page(page, current_page):
                        current_page += 1
                        # Add delay after page navigation
                        self.random_delay(*self.delay_config["page_load_delay"])
                    else:
                        logger.info("Could not navigate to next page, ending pagination")
                        break

                logger.info("Closing browser...")
                browser.close()

        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}", exc_info=True)
            # Save page content for debugging
            if 'page' in locals():
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                logger.info("Saved error page content to error_page.html")
            
            # Save what we have so far even if there's an error
            if all_hotels_data:
                self.save_checkpoint(all_hotels_data, current_page)

        logger.info(f"Scraping completed. Extracted data for {len(all_hotels_data)} hotels across {current_page} pages")
        return all_hotels_data

    def save_to_json(self, data: List[Dict], filename: str):
        """Save scraped data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")

    def get_country_url(self, country: str) -> str:
        """Generate URL for specific country"""
        base_params = (
            "?checkin_day=09&checkin_month=05&checkin_year=2025"
            "&checkout_day=10&checkout_month=05&checkout_year=2025"
            "&adults=2&date_format=dd%2Fmm%2Fyy&cur=GBP&visitor_country_code=UK"
        )
        return f"https://www.travelmyth.com/{country}/Hotels/tennis{base_params}"

    def scrape_all_countries(self):
        """Scrape tennis hotels for all European countries"""
        all_countries_data = []
        
        for country in self.european_countries:
            try:
                logger.info(f"Starting scraping for country: {country}")
                country_hotels = []
                
                # Get base URL for current country
                base_url = self.get_country_url(country)
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(user_agent=self.headers["User-Agent"])
                    page = context.new_page()
                    
                    # Get first page and total pages
                    response = page.goto(base_url, wait_until="networkidle")
                    total_pages = self.get_total_pages(page)
                    logger.info(f"Found {total_pages} pages for {country}")
                    
                    # Simply iterate through pages by adding &page=X to URL
                    for current_page in range(1, total_pages + 1):
                        page_url = f"{base_url}&page={current_page}" if current_page > 1 else base_url
                        logger.info(f"Scraping page {current_page}: {page_url}")
                        
                        # Navigate directly to page URL
                        response = page.goto(page_url, wait_until="networkidle")
                        
                        # Extract hotels for current page
                        page_hotels = []
                        hotel_elements = page.query_selector_all(".hotel_repeat")
                        for hotel_element in hotel_elements:
                            hotel_data = self.extract_hotel_data(hotel_element)
                            if hotel_data:
                                hotel_data['source_country'] = country
                                hotel_data['page_number'] = current_page
                                page_hotels.append(hotel_data)
                        
                        # Save checkpoint for current page only
                        self.save_to_json(page_hotels, f'tennis_hotels_{country.lower()}_checkpoint_page_{current_page}.json')
                        country_hotels.extend(page_hotels)
                    
                    browser.close()
                
                # Save country data
                self.save_to_json(country_hotels, f'tennis_hotels_{country.lower()}.json')
                all_countries_data.extend(country_hotels)
                
            except Exception as e:
                logger.error(f"Error scraping country {country}: {str(e)}")
                continue
        
        self.save_to_json(all_countries_data, 'tennis_hotels_europe.json')
        return all_countries_data

def main():
    # Initialize scraper
    scraper = TravelmythScraper()
    
    # Scrape all European countries
    hotels_data = scraper.scrape_all_countries()
    
    logger.info(f"Scraped total of {len(hotels_data)} hotels across Europe")

if __name__ == "__main__":
    main() 