from pyvesync import VeSync
import myfitnesspal

def get_data():
    import garmin_fit_sdk
    import requests
    client = garmin_fit_sdk.GarminConnectAPIClient(username="ferocemarcello@gmail.com", password="")
    activities = client.get_activities()
    for activity in activities:
        print(activity.name)

    return ""
