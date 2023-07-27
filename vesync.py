from garminconnect import Garmin

def get_data():
    client = Garmin('ferocemarcello@gmail.com', 'password')
    username = client.username
    print(username)
    return username
