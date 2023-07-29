"""Class for downloading health data from Garmin Connect."""

__author__ = "Tom Goetz"
__copyright__ = "Copyright Tom Goetz"
__license__ = "GPL"

import os
import re
import datetime
import time
import tempfile
import zipfile
import json
import cloudscraper
from tqdm import tqdm

import fitfile.conversions as conversions

from garmin_connect_config_manager import GarminConnectConfigManager
from config_manager import ConfigManager
from rest_client_pers import RestClientPers


class Download:
    """Class for downloading health data from Garmin Connect."""

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

    garmin_connect_user_summary_url = "proxy/usersummary-service/usersummary"
    garmin_connect_daily_summary_url = garmin_connect_user_summary_url + "/daily"
    garmin_connect_daily_hydration_url = garmin_connect_user_summary_url + "/hydration/allData"

    # https://connect.garmin.com/modern/proxy/usersummary-service/usersummary/hydration/allData/2019-11-29

    garmin_headers = {'NK': 'NT'}

    def __init__(self):
        """Create a new Download class instance."""
        self.session = cloudscraper.CloudScraper()
        self.sso_rest_client = RestClientPers(self.session, 'sso.garmin.com', 'sso', aditional_headers=self.garmin_headers)
        self.modern_rest_client = RestClientPers(self.session, 'connect.garmin.com', 'modern',
                                             aditional_headers=self.garmin_headers)
        self.activity_service_rest_client = RestClientPers.inherit(self.modern_rest_client,
                                                               "proxy/activity-service/activity")
        self.download_service_rest_client = RestClientPers.inherit(self.modern_rest_client, "proxy/download-service/files")
        self.gc_config = GarminConnectConfigManager()
        self.download_days_overlap = 3  # Existing downloaded data will be re-downloaded and overwritten if it is within this number of days of now.

    def __get_json(self, page_html, key):
        found = re.search(key + r" = (\{.*\});", page_html, re.M)
        if found:
            json_text = found.group(1).replace('\\"', '"')
            return json.loads(json_text)

    def login(self):
        """Login to Garmin Connect."""
        profile_dir = ConfigManager.get_or_create_fit_files_dir()
        username = self.gc_config.get_user()
        password = self.gc_config.get_password()
        if not username or not password:
            print("Missing config: need username and password. Edit GarminConnectConfig.json.")
            return

        get_headers = {
            'Referer': self.garmin_connect_login_url
        }
        params = {
            'service': self.modern_rest_client.url(),
            'webhost': self.garmin_connect_base_url,
            'source': self.garmin_connect_login_url,
            'redirectAfterAccountLoginUrl': self.modern_rest_client.url(),
            'redirectAfterAccountCreationUrl': self.modern_rest_client.url(),
            'gauthHost': self.sso_rest_client.url(),
            'locale': 'en_US',
            'id': 'gauth-widget',
            'cssUrl': self.garmin_connect_css_url,
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
        response = self.sso_rest_client.get(self.garmin_connect_sso_login, get_headers, params)
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
        response = self.sso_rest_client.post(self.garmin_connect_sso_login, post_headers, params, data)
        found = re.search(r"\?ticket=([\w-]*)", response.text, re.M)
        params = {
            'ticket': found.group(1)
        }
        response = self.modern_rest_client.get('', params=params)
        self.user_prefs = self.__get_json(response.text, 'VIEWER_USERPREFERENCES')
        if profile_dir:
            self.modern_rest_client.save_json_to_file(f'{profile_dir}/profile.json', self.user_prefs)
        self.display_name = self.user_prefs['displayName']
        self.social_profile = self.__get_json(response.text, 'VIEWER_SOCIAL_PROFILE')
        self.full_name = self.social_profile['fullName']
        return True

    def __unzip_files(self, outdir):
        """Unzip and downloaded zipped files into the directory supplied."""
        for filename in os.listdir(self.temp_dir):
            match = re.search(r'.*\.zip', filename)
            if match:
                full_pathname = f'{self.temp_dir}/{filename}'
                with zipfile.ZipFile(full_pathname, 'r') as files_zip:
                    files_zip.extractall(outdir)

    def __get_stat(self, stat_function, directory, date, days, overwrite):
        for day in tqdm(range(0, days), unit='days'):
            download_date = date + datetime.timedelta(days=day)
            # always overwrite for yesterday and today since the last download may have been a partial result
            delta = datetime.datetime.now().date() - download_date
            stat_function(directory, download_date, overwrite or delta.days <= self.download_days_overlap)
            # pause for a second between every page access
            time.sleep(1)

    def __get_summary_day(self, directory_func, date, overwrite=False):
        date_str = date.strftime('%Y-%m-%d')
        params = {
            'calendarDate': date_str,
            '_': str(conversions.dt_to_epoch_ms(conversions.date_to_dt(date)))
        }
        url = f'{self.garmin_connect_daily_summary_url}/{self.display_name}'
        json_filename = f'{directory_func(date.year)}/daily_summary_{date_str}'
        self.modern_rest_client.download_json_file(url, json_filename, overwrite, params)

    def get_daily_summaries(self, directory_func, date, days, overwrite):
        """Download the daily summary data from Garmin Connect and save to a JSON file."""
        self.__get_stat(self.__get_summary_day, directory_func, date, days, overwrite)

    def __get_monitoring_day(self, date):
        zip_filename = f'{self.temp_dir}/{date}.zip'
        url = f'wellness/{date.strftime("%Y-%m-%d")}'
        self.download_service_rest_client.download_binary_file(url, zip_filename)

    def get_monitoring(self, directory_func, date, days):
        """Download the daily monitoring data from Garmin Connect, unzip and save the raw files."""
        for day in tqdm(range(0, days + 1), unit='days'):
            day_date = date + datetime.timedelta(day)
            self.temp_dir = tempfile.mkdtemp()
            self.__get_monitoring_day(day_date)
            self.__unzip_files(directory_func(day_date.year))
            # pause for a second between every page access
            time.sleep(1)

    def __get_weight_day(self, directory, day, overwrite=False):
        date_str = day.strftime('%Y-%m-%d')
        params = {
            'startDate': date_str,
            'endDate': date_str,
            '_': str(conversions.dt_to_epoch_ms(conversions.date_to_dt(day)))
        }
        json_filename = f'{directory}/weight_{date_str}'
        self.modern_rest_client.download_json_file(self.garmin_connect_weight_url, json_filename, overwrite, params)

    def get_weight(self, directory, date, days, overwrite):
        """Download the sleep data from Garmin Connect and save to a JSON file."""
        self.__get_stat(self.__get_weight_day, directory, date, days, overwrite)

    def __get_activity_summaries(self, start, count):
        params = {
            'start': str(start),
            "limit": str(count)
        }
        response = self.modern_rest_client.get(self.garmin_connect_activity_search_url, params=params)
        return response.json()

    def __save_activity_details(self, activity_id_str):
        self.activity_service_rest_client.download_json_file(leaf_route = activity_id_str)

    def __save_activity_file(self, activity_id_str):
        zip_filename = f'{self.temp_dir}/activity_{activity_id_str}.zip'
        url = f'activity/{activity_id_str}'
        self.download_service_rest_client.download_binary_file(url, zip_filename)

    def get_activities(self, count):
        """Download activities files from Garmin Connect."""
        activities = self.__get_activity_summaries(0, count)
        for activity in tqdm(activities or [], unit='activities'):
            activity_id_str = str(activity['activityId'])
            activity_name_str = conversions.printable(activity['activityName'])
            self.__save_activity_details(activity_id_str=activity_id_str)
            # pause for a second between every page access
            time.sleep(1)
        return activities
    def get_activity_types(self):
        return self.activity_service_rest_client.download_json_file(leaf_route='activityTypes')

    def __get_sleep_day(self, directory, date, overwrite=False):
        json_filename = f'{directory}/sleep_{date}'
        params = {
            'date': date.strftime("%Y-%m-%d"),
            'nonSleepBufferMinutes': 60
        }
        url = f'{self.garmin_connect_sleep_daily_url}/{self.display_name}'
        self.modern_rest_client.download_json_file(url, json_filename, overwrite, params)

    def get_sleep(self, directory, date, days, overwrite):
        """Download the sleep data from Garmin Connect and save to a JSON file."""
        self.__get_stat(self.__get_sleep_day, directory, date, days, overwrite)

    def __get_rhr_day(self, directory, day, overwrite=False):
        date_str = day.strftime('%Y-%m-%d')
        json_filename = f'{directory}/rhr_{date_str}'
        params = {
            'fromDate': date_str,
            'untilDate': date_str,
            'metricId': 60
        }
        url = f'{self.garmin_connect_rhr}/{self.display_name}'
        self.modern_rest_client.download_json_file(url, json_filename, overwrite, params)

    def get_rhr(self, directory, date, days, overwrite):
        """Download the resting heart rate data from Garmin Connect and save to a JSON file."""
        self.__get_stat(self.__get_rhr_day, directory, date, days, overwrite)

    def __get_hydration_day(self, directory_func, day, overwrite=False):
        date_str = day.strftime('%Y-%m-%d')
        json_filename = f'{directory_func(day.year)}/hydration_{date_str}'
        url = f'{self.garmin_connect_daily_hydration_url}/{date_str}'
        self.modern_rest_client.download_json_file(url, json_filename, overwrite)

    def get_hydration(self, directory_func, date, days, overwrite):
        """Download the hydration data from Garmin Connect and save to a JSON file."""
        self.__get_stat(self.__get_hydration_day, directory_func, date, days, overwrite)
