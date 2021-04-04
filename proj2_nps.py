#################################
##### Name:
##### Uniqname:
#################################

from bs4 import BeautifulSoup
import requests
import json
import secrets # file that contains your API key

CACHE_FILENAME = "cache.json"

def open_cache():
    ''' opens the cache file if it exists and loads the JSON into
    a dictionary, which it then returns.
    if the cache file doesn't exist, creates a new cache dictionary
    Parameters
    ----------
    None
    Returns
    -------
    The opened cache
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    ''' saves the current state of the cache to disk
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close() 

CACHE = open_cache()

class NationalSite:
    '''a national site

    Instance Attributes
    -------------------
    category: string
        the category of a national site (e.g. 'National Park', '')
        some sites have blank category.
    
    name: string
        the name of a national site (e.g. 'Isle Royale')

    address: string
        the city and state of a national site (e.g. 'Houghton, MI')

    zipcode: string
        the zip-code of a national site (e.g. '49931', '82190-0168')

    phone: string
        the phone of a national site (e.g. '(616) 319-7906', '307-344-7381')
    '''
    def __init__(self, category, name, address, zipcode, phone):
        self.category = category
        self.name = name
        self.address = address
        self.zipcode = zipcode
        self.phone = phone
    def info(self):
        ''' String representation of a National Site object
        Parameters
        ----------
        None

        Returns
        -------
        string
            Includes identifying information for a National Site

        '''
        return f"{self.name} ({self.category}): {self.address} {self.zipcode}"

def json_to_NationalSite(json):
    ''' Converts json dictionary to National Site object

    Parameters
    ----------
    json
        json dictionary with keys corresponding to National Site object attributes

    Returns
    -------
    National Site object

    '''
    return NationalSite(json['category'], json['name'], json['address'], json['zipcode'], json['phone'])

def build_state_url_dict():
    ''' Make a dictionary that maps state name to state page url from "https://www.nps.gov"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a state name and value is the url
        e.g. {'michigan':'https://www.nps.gov/state/mi/index.htm', ...}
    '''
    if 'states' in CACHE:
        print("Using cache")
        return CACHE['states']
    else:
        print("Fetching")
        state_dict = {}
        html = requests.get('https://www.nps.gov/index.htm').text
        soup = BeautifulSoup(html, 'html.parser')
        state_list = soup.find_all('ul', class_= "dropdown-menu SearchBar-keywordSearch")
        list_items = state_list[0].find_all('a')
        for item in list_items:
            state_dict[item.text.strip().lower()] = 'https://www.nps.gov' + item['href']
        CACHE['states'] = state_dict
        save_cache(CACHE)
        return state_dict

def get_site_instance(site_url):
    '''Make an instances from a national site URL.
    
    Parameters
    ----------
    site_url: string
        The URL for a national site page in nps.gov
    
    Returns
    -------
    instance
        a national site instance
    '''
    if site_url in CACHE:
        print("Using cache")
        return json_to_NationalSite(CACHE[site_url])
    else:
        print("Fetching")
        html = requests.get(site_url).text
        soup = BeautifulSoup(html, 'html.parser')
        div_category = soup.find(class_="Hero-designationContainer")
        category = div_category.find('span', class_="Hero-designation").contents[0]
        div_name = soup.find(class_="Hero-titleContainer clearfix")
        name = div_name.find('a').contents[0]
        city = soup.find('span', itemprop="addressLocality").contents[0].strip()
        state = soup.find('span', itemprop="addressRegion").contents[0].strip()
        address = city + ', ' + state
        zipcode = soup.find('span', itemprop="postalCode").contents[0].strip()
        phone = soup.find('span', itemprop="telephone").contents[0].strip()
        instance = NationalSite(category, name, address, zipcode, phone)
        CACHE[site_url] = instance.__dict__
        save_cache(CACHE)
        return instance


def get_sites_for_state(state_url):
    '''Make a list of national site instances from a state URL.
    
    Parameters
    ----------
    state_url: string
        The URL for a state page in nps.gov
    
    Returns
    -------
    list
        a list of national site instances
    '''
    site_instances = []
    if state_url in CACHE:
        print("Using cache")
        for site in CACHE[state_url]:
            site_instances.append(json_to_NationalSite(site))
    else:
        print("Fetching")
        site_instances_cache = []
        html = requests.get(state_url).text
        soup = BeautifulSoup(html, 'html.parser')
        sites = soup.find(id = 'parkListResultsArea')
        headers = sites.find_all('h3')
        for header in headers:
            url = header.find('a')
            instance = get_site_instance('https://www.nps.gov' + url['href'] + 'index.htm')
            site_instances.append(instance)
            site_instances_cache.append(instance.__dict__)
        CACHE[state_url] = site_instances_cache
        save_cache(CACHE)
    return site_instances

def get_nearby_places(site_object):
    '''Obtain API data from MapQuest API.
    
    Parameters
    ----------
    site_object: object
        an instance of a national site
    
    Returns
    -------
    dict
        a converted API return from MapQuest API
    '''
    if site_object.zipcode in CACHE:
        print("Using cache")
        return CACHE[site_object.zipcode]
    else:
        print("Fetching")
        BASE_URL = f'http://www.mapquestapi.com/search/v2/radius?key={secrets.API_KEY}&radius=10&maxMatches=10&ambiguities=ignore&origin='
        response = requests.get(BASE_URL + f'{site_object.zipcode}')
        results = response.json()
        CACHE[site_object.zipcode] = results
        save_cache(CACHE)
        return results

def nearby_places_info(place_dict):
    ''' Returns description of a place

    Parameters
    ----------
    dict
        Dictionary obtained from MapQuest API

    Returns
    -------
    string
        Description of place
    '''
    name = place_dict["name"]

    if not place_dict['group_sic_code_name_ext']:
        category = 'no category'
    else:
        category = place_dict['group_sic_code_name_ext']

    if not place_dict['address']:
        address = 'no address'
    else:
        address = place_dict['address']

    if not place_dict['city']:
        city = 'no city'
    else:
        city = place_dict['city']

    return f"{name} ({category}): {address}, {city}"

if __name__ == "__main__":
    states = build_state_url_dict()
    while True:
        inp = input('Enter a state name (e.g. Michigan, michigan) or "exit": ').lower()
        if inp in states:
            sites = get_sites_for_state(states[inp])
            print("------------------------------------")
            print(f"List of national sites in {inp}")
            print("------------------------------------")
            count = 1
            for site in sites:
                print(f"[{count}] " + site.info())
                count += 1
            while True:
                print("\n------------------------------------")
                inp = input('Choose the number for detailed search or "exit" or "back": ').lower()
                if inp.isnumeric():
                    if int(inp) in range (1, count+1):
                        places = get_nearby_places(sites[int(inp)-1])
                        print("------------------------------------")
                        print(f"Places near {sites[int(inp)-1].name}")
                        print("------------------------------------")
                        count1 = 1
                        for place in places["searchResults"]:
                            print(f'[{count1}] ' + nearby_places_info(place["fields"]))
                            count1 += 1
                    else:
                        print('[Error] Invalid input')
                elif inp == 'exit':
                    exit()
                elif inp == 'back':
                    break
                else:
                    print('[Error] Invalid input')
        elif inp == 'exit':
            break
        else:
            print("[Error] Enter proper state name\n")

