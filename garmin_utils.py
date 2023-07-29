import json
import re

import cloudscraper
from idbutils import RestClient
import datetime
from config_manager import ConfigManager
from download import Download
from garmin_connect_config_manager import GarminConnectConfigManager
from statistics import Statistics
from garmindb.garmindb import GarminDb, Attributes, Sleep, Weight, RestingHeartRate, MonitoringDb, MonitoringHeartRate, \
    ActivitiesDb, GarminSummaryDb

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
            'username': self.username,
            'password': self.password,
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
        self.user_prefs = self.__get_json(response.text, 'VIEWER_USERPREFERENCES')
        self.display_name = self.user_prefs['displayName']
        self.social_profile = self.__get_json(response.text, 'VIEWER_SOCIAL_PROFILE')
        self.full_name = self.social_profile['fullName']
        return True

    def __get_json(self, page_html, key):
        found = re.search(key + r" = (\{.*\});", page_html, re.M)
        if found:
            json_text = found.group(1).replace('\\"', '"')
            return json.loads(json_text)

    def __get_date_and_days(self, db, latest, table, col, stat_name):
        if latest:
            last_ts = table.latest_time(db, col)
            if last_ts is None:
                date, days = self.gc_config.stat_start_date(stat_name)
            else:
                # start from the day before the last day in the DB
                date = last_ts.date() if isinstance(last_ts, datetime.datetime) else last_ts
                days = max((datetime.date.today() - date).days, 1)
        else:
            date, days = self.gc_config.stat_start_date(stat_name)
            days = min((datetime.date.today() - date).days, days)
        return date, days

    def download_data(self, overwrite, latest):
        """Download selected activity types from Garmin Connect"""

        download = Download()

        '''if latest:
            activity_count = self.gc_config.latest_activity_count()
        else:
            activity_count = self.gc_config.all_activity_count()
        activities_dir = ConfigManager.get_or_create_activities_dir()'''
        activity_types = download.get_activity_types()
        activities = download.get_activities(count=10)

        date, days = self.__get_date_and_days(MonitoringDb(self.db_params_dict), latest, MonitoringHeartRate,
                                              MonitoringHeartRate.heart_rate, 'monitoring')
        if days > 0:
            download.get_daily_summaries(ConfigManager.get_or_create_monitoring_dir, date, days, overwrite)
            download.get_hydration(ConfigManager.get_or_create_monitoring_dir, date, days, overwrite)
            download.get_monitoring(ConfigManager.get_or_create_monitoring_dir, date, days)

        date, days = self.__get_date_and_days(GarminDb(self.db_params_dict), latest, Sleep, Sleep.total_sleep,
                                              'sleep')
        if days > 0:
            sleep_dir = ConfigManager.get_or_create_sleep_dir()
            download.get_sleep(sleep_dir, date, days, overwrite)

        date, days = self.__get_date_and_days(GarminDb(self.db_params_dict), latest, Weight, Weight.weight,
                                              'weight')
        if days > 0:
            weight_dir = ConfigManager.get_or_create_weight_dir()
            download.get_weight(weight_dir, date, days, overwrite)

        date, days = self.__get_date_and_days(GarminDb(self.db_params_dict), latest, RestingHeartRate,
                                              RestingHeartRate.resting_heart_rate, 'rhr')
        if days > 0:
            rhr_dir = ConfigManager.get_or_create_rhr_dir()
            download.get_rhr(rhr_dir, date, days, overwrite)

        return activity_count

    def get_data(self):
        login_result = self.login()
        print("Login status: " + str(login_result))
        downloaded_data = self.download_data(overwrite=False, latest=False)
        return downloaded_data

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.user_prefs = None
        self.display_name = None
        self.social_profile = None
        self.full_name = None
        self.gc_config = GarminConnectConfigManager()
