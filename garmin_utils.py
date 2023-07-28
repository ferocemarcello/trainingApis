import json
import re

import cloudscraper
from idbutils import RestClient

garmin_connect_base_url = "https://connect.garmin.com"
garmin_connect_enus_url = garmin_connect_base_url + "/en-US"
garmin_connect_sso_login = 'signin'
garmin_connect_login_url = garmin_connect_enus_url + "/signin"
garmin_connect_css_url = 'https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css'
garmin_connect_privacy_url = "//connect.garmin.com/en-U/privacy"
garmin_connect_user_profile_url = "proxy/userprofile-service/userprofile"
garmin_connect_wellness_url = "proxy/wellness-service/wellness"
garmin_connect_sleep_daily_url = garmin_connect_wellness_url + "/dailySleepData"
garmin_connect_rhr = "proxy/userstats-service/wellness/daily"
garmin_connect_weight_url = "proxy/weight-service/weight/dateRange"
garmin_connect_activity_search_url = "proxy/activitylist-service/activities/search/activities"
garmin_connect_usersummary_url = "proxy/usersummary-service/usersummary"
garmin_connect_daily_summary_url = garmin_connect_usersummary_url + "/daily"
garmin_connect_daily_hydration_url = garmin_connect_usersummary_url + "/hydration/allData"

garmin_headers = {'NK': 'NT'}
session = cloudscraper.CloudScraper()
modern_rest_client = RestClient(session, 'connect.garmin.com', 'modern', aditional_headers=garmin_headers)
sso_rest_client = RestClient(session, 'sso.garmin.com', 'sso', aditional_headers=garmin_headers)


class GarminUtils:

    def login(self):
        """Login to Garmin Connect."""
        get_headers = {
            'Referer': garmin_connect_login_url
        }
        params = {
            'service': modern_rest_client.url(),
            'webhost': garmin_connect_base_url,
            'source': garmin_connect_login_url,
            'redirectAfterAccountLoginUrl': modern_rest_client.url(),
            'redirectAfterAccountCreationUrl': modern_rest_client.url(),
            'gauthHost': sso_rest_client.url(),
            'locale': 'en_US',
            'id': 'gauth-widget',
            'cssUrl': garmin_connect_css_url,
            'privacyStatementUrl': '//connect.garmin.com/en-US/privacy/',
            'clientId': 'GarminConnect',
            'rememberMeShown': 'true',
            'rememberMeChecked': 'false',
            'createAccountShown': 'true',
            'openCreateAccount': 'false',
            'displayNameShown': 'false',
            'consumeServiceTicket': 'false',
            'initialFocus': 'true',
            'embedWidget': 'false',
            'generateExtraServiceTicket': 'true',
            'generateTwoExtraServiceTickets': 'false',
            'generateNoServiceTicket': 'false',
            'globalOptInShown': 'true',
            'globalOptInChecked': 'false',
            'mobile': 'false',
            'connectLegalTerms': 'true',
            'locationPromptShown': 'true',
            'showPassword': 'true'
        }
        response = sso_rest_client.get(garmin_connect_sso_login, get_headers, params)
        found = re.search(r"name=\"_csrf\" value=\"(\w*)", response.text, re.M)
        data = {
            'username': username,
            'password': password,
            'embed': 'false',
            '_csrf': found.group(1)
        }
        post_headers = {
            'Referer': response.url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = sso_rest_client.post(garmin_connect_sso_login, post_headers, params, data)
        found = re.search(r"\?ticket=([\w-]*)", response.text, re.M)
        params = {
            'ticket': found.group(1)
        }
        response = modern_rest_client.get('', params=params)
        user_prefs = self.__get_json(response.text, 'VIEWER_USERPREFERENCES')
        modern_rest_client.save_json_to_file('./profile.json', self.user_prefs)
        self.display_name = self.user_prefs['displayName']
        social_profile = self.__get_json(response.text, 'VIEWER_SOCIAL_PROFILE')
        full_name = self.social_profile['fullName']
        return True

    def __get_json(self, page_html, key):
        found = re.search(key + r" = (\{.*\});", page_html, re.M)
        if found:
            json_text = found.group(1).replace('\\"', '"')
            return json.loads(json_text)

    def get_data(self):
        login_result = self.login()
        print(login_result)
        return login_result

    def __init__(self, name, password):
        self.name = name
        self.password = password
