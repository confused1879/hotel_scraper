# Scraping configuration
SCRAPING_CONFIG = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,  # seconds
    "PAGE_LOAD_TIMEOUT": 30000,  # milliseconds
    "REQUEST_DELAY": 2,  # seconds between requests
}

# Selectors for hotel elements
SELECTORS = {
    "HOTEL_ITEM": ".hotel-item",
    "HOTEL_NAME": ".hotel-name",
    "HOTEL_LOCATION": ".hotel-location",
    "HOTEL_RATING": ".hotel-rating",
    "HOTEL_PRICE": ".hotel-price",
    "HOTEL_AMENITIES": ".hotel-amenities",
    "TENNIS_FACILITIES": ".tennis-facilities"
} 