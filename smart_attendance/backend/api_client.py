import requests
from config.settings import API_URL

def get_session_status():
    """ Fetches the current session status from the backend """
    try:
        response = requests.get(API_URL)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching session status: {e}")
        return None
    

def listen_for_session():
    """ Listens for real-time session updates from the backend (SSE). """
    while True:
        try:
            with requests.get(f"{API_URL}/events", stream=True) as response:
                for line in response.iter_lines():
                    if line:
                        session_type = line.decode("utf-8").replace("data: ", "")  
                        yield session_type  # Continuously listen for updates
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to SSE: {e}")
