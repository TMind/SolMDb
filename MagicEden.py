import requests, re, json
from NetApi import NetApi  
from soldb import parse_arguments
from GlobalVariables import global_vars as gv

def get_collection_listings(collection_symbol):
    """
    Fetches the listings for the given collection symbol from Magic Eden's API.
    """
    url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection_symbol}/listings"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return None


# Function to handle pagination and fetch all listings
def fetch_all_magiceden_listings(collection_symbol, myApi, args, limit=100):
    """
    Fetches all listings for a given collection symbol from Magic Eden's API, handling pagination.
    Passes each page of listings to process_magiceden_listings for further processing.
    """
    url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection_symbol}/listings"
    offset = 0  # Start pagination from 0
    headers = {
        'ME-Pub-API-Metadata': '{"paging": true}'  # Request pagination metadata
    }
    all_decks = []

    while True:
        try:
            # Set the request parameters for pagination
            params = {"limit": limit, "offset": offset}
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Break the loop if no listings are found
            if not data:
                print(f"No listings found at offset {offset}. Ending pagination.")
                break

            print(f"Processing {len(data)} listings from offset {offset}")

            # Process the current page of listings
            net_data = process_magiceden_listings(data, myApi, args)
            all_decks.extend(net_data)

            # Fetch pagination metadata from the response headers
            metadata = response.headers.get('ME-Pub-API-Metadata')
            if metadata:
                metadata = json.loads(metadata)
                paging_info = metadata.get('paging', {})
                total = paging_info.get('total', 0)
                end = paging_info.get('end', 0)

                print(f"Total listings: {total}, End: {end}")

                # If we've processed all listings, stop pagination
                if end >= total:
                    print(f"All listings processed. Total: {total}")
                    break

            # Increment offset for the next page
            offset += limit

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            break
        except Exception as err:
            print(f"An error occurred: {err}")
            break

    return all_decks

def process_magiceden_listings(listings, myApi, args):
    """
    Processes listings from Magic Eden and fetches deck data using deck links.
    Only extracts the deck_link and fetches the actual deck data from that link via `myApi.request_decks`.
    """
    net_data = []

    if listings:
        identifier = "Processing listing"
        gv.reset_progress(identifier)
        gv.update_progress(identifier, 0, len(listings))
        for idx, listing in enumerate(listings, start=1):            
            token = listing.get('token', {})
            price = listing.get('price', 0.0)
            owner = token.get('owner', '')
            attributes = token.get('attributes', [])
            deck_link = None
            
            # Extract the deck_link from the attributes
            for attribute in attributes:
                if attribute.get('trait_type') == 'Deck Link':
                    deck_link = attribute.get('value')
                    break
                
            if deck_link:
                # Extract the deck ID from the deck link using regex
                match = re.search(r'\/([^\/]+)$', deck_link)
                if match:
                    deck_id = match.group(1)
                    gv.update_progress("Processing listing", message=f"Fetching deck data for ID: {deck_id}")
                    #print(f"Fetching deck data for ID: {deck_id}")
                    
                    # Fetch the deck data using myApi.request_decks
                    deck_data = myApi.request_decks(
                        id=deck_id,
                        type=args.type,
                        username='tmind',
                        filename=None,
                        params={'inclCards': 'true', 
                                'inclUsers': 'false', 
                                'inclPvE': 'false'}  
                    )
                    
                    if deck_data:
                        deck_data[0]['price'] = price  # Add the price to the deck data
                        deck_data[0]['owner'] = owner  # Add the owner to the deck data
                        net_data.extend(deck_data)  # Append the fetched deck data to the list
                    else:
                        print(f"No data returned for deck with ID: {deck_id}")
    
    return net_data

def main():
    """
    Main function to fetch listings and process the decks using NetApi.
    """
    # Initialize NetApi
    myApi = NetApi()  # You may need to pass additional arguments if required by the NetApi constructor
    
    # Setup arguments (these might need to be adjusted based on your setup)
    arguments = ['--type', 'deck']
    args = parse_arguments(arguments)

    # The collection symbol for SFGC is 'sfgc'
    collection_symbol = 'sfgc'
    
    # Fetch all listings with pagination and process them
    all_decks = fetch_all_magiceden_listings(collection_symbol, myApi, args)    

if __name__ == "__main__":
    main()