from __future__ import print_function
import http.server
import json
import os.path
import webbrowser
from datetime import timedelta
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import unquote
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium import webdriver
import pandas as pd

import requests
import webbrowser
import tkinter as tk
from accesslink import AccessLink

import garmin_utils

client_id_google = '288512384213-h737qune0i8k8i13p49sb73taa20l810.apps.googleusercontent.com'
client_secret_google = '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'

client_id_polar = 'ea15e66e-0f27-4faa-8cf2-2928d1262509'
client_secret_polar = '0e1b5074-3436-4d5d-b286-ae4d1fe2f83c'

client_id_strava = '84341'
client_secret_strava = 'd982e50eb5253a32dd7665a4400be9bbd2bf7dfc'
access_token_strava = 'de5a54102f1c72cea5ec504632997c0f2a9559dd'
refresh_token_strava = 'f61e3ebe8bc18b00b16556dc52f0c1505f3450d2'

base64encondedClientIdSecret = 'ZWExNWU2NmUtMGYyNy00ZmFhLThjZjItMjkyOGQxMjYyNTA5OjBlMWI1MDc0LTM0MzYtNGQ1ZC1iMjg2LWFlNGQxZmUyZjgzYw=='


def get_data_from_spreadsheet(service, fileName, key_name, rangee):
    return service.spreadsheets().values().get(spreadsheetId=get_spread_sheet_id(file_name=fileName, key_name=key_name),
                                               range=rangee).execute()


def get_last_row(service, file_name='spreadSheetId.json', key_name='SPREADSHEET_ID'):
    all_range = 'A1:F'
    result = get_data_from_spreadsheet(service=service, fileName=file_name, key_name=key_name, rangee=all_range)
    return len(result.get('values'))


def get_last_date(service, fileName='spreadSheetId.json', keyName='SPREADSHEET_ID'):
    date_range = 'A1:A'
    result = get_data_from_spreadsheet(service=service, fileName=fileName, key_name=keyName, rangee=date_range)
    return result.get('values')[len(result.get('values')) - 1][0]


def increment_date_by_number_of_days(date_time_str='01∕01/2000', number_of_days=1):
    date_time_obj = datetime.strptime(date_time_str + ' 00:00:00', '%d/%m/%Y %H:%M:%S')
    date_time_obj += timedelta(days=number_of_days)
    return date_time_obj.strftime("%d/%m/%Y")


def get_array_of_dates(last_date, number_of_days):
    date_array = []
    for dayIncrement in range(1, number_of_days + 1):
        date_array.append(increment_date_by_number_of_days(date_time_str=last_date, number_of_days=dayIncrement))
    return date_array


def get_spread_sheet_id(file_name='spreadSheetId.json', key_name='SPREADSHEET_ID'):
    with open(file_name) as f:
        data = json.load(f)
    f.close()
    return data.get(key_name)


# If modifying these scopes, delete the file token.json.
def get_credentials(token_file='token.json', scopes=None):
    if scopes is None:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        credentials = Credentials.from_authorized_user_file(token_file, scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', scopes)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(credentials.to_json())
    return credentials


def write_values_in_range(service, file_name, key_name, rangee, value_input_option, body):
    result = service.spreadsheets().values().update(
        spreadsheetId=get_spread_sheet_id(file_name=file_name, key_name=key_name), range=rangee,
        valueInputOption=value_input_option, body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))


def get_data_frame_from_values(dates, yes_no_training_values, training_feeling_values, general_feeling_values, weight_values,
                               note_values):
    df = pd.DataFrame()
    dateDataFrame = pd.DataFrame({
        'Date': dates
    })
    general_data_frame = pd.DataFrame({
        'Training_yes_no': yes_no_training_values,
        'Training_feeling': training_feeling_values,
        'General_feeling': general_feeling_values,
        'Weight': weight_values,
        'Notes': weight_values
    })
    df['Date'] = dateDataFrame
    df['Training_yes_no'] = general_data_frame['Training_yes_no']
    df['Training_feeling'] = general_data_frame['Training_yes_no']
    df['General_feeling'] = general_data_frame['General_feeling']
    df['Weight'] = general_data_frame['Weight']
    df['Notes'] = general_data_frame['Notes']

    return df


def get_polar_oauth_code(self_client_id_polar):
    request_url = 'https://flow.polar.com/oauth2/authorization?response_type=code&scope=accesslink.read_all&client_id=' + self_client_id_polar
    '''
    result = requests.get(request_url)
    resp = webbrowser.open(request_url)
    '''
    return request_url


def get_polar_access_token(oauth_code):
    request_url = 'https://polarremote.com/v2/oauth2/token'
    headers = {"Authorization": "Basic ea15e66e-0f27-4faa-8cf2-2928d1262509:0e1b5074-3436-4d5d-b286-ae4d1fe2f83c"}
    body = {"grant_type": "authorization_code", "code": oauth_code}
    result = requests.post(request_url, headers=headers, json=body)
    return result


def do_shit_with_polar_and_strava():
    oauth_code_polar = get_polar_oauth_code(self_client_id_polar=client_id_polar, client_secret_polar=client_secret_polar)
    oauth_code_polar = '97e6e13bcc23f5160509d2af10769ae6'
    polar_access_token = get_polar_access_token(oauth_code=oauth_code_polar)

    headers = {"Authorization": "Bearer de5a54102f1c72cea5ec504632997c0f2a9559dd"}

    result = requests.get('https://www.strava.com/api/v3/athlete', headers=headers)

    url = 'http://www.strava.com/oauth/authorize?client_id=' + client_id_strava + '&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=read'
    response = requests.get(url, verify=False, allow_redirects=True)

    if response.status_code == 200:
        page = response.text
        # parse the html using beautifulsoup
        html_content = BeautifulSoup(page, 'html.parser')
        soup = html_content
        href = soup.find("link", href=True)
        href = href['href']

        new_url = unquote(unquote(href))

    result = webbrowser.open(
        'http://www.strava.com/oauth/authorize?client_id=' + client_id_strava + '&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=read')


def add_gui():
    window = tk.Tk()

    entry = tk.Entry(width=40, bg="white", fg="black")
    entry.pack()

    entry.insert(0, "What is your name?")

    window.mainloop()
    print("")


# replace with your own http handlers
def wait_for_request(server_class=http.server,
                     handler_class=http.server.BaseHTTPRequestHandler):
    server_address = ('', 5000)
    httpd = server_class.HTTPServer(server_address=server_address, RequestHandlerClass=handler_class)
    return httpd.handle_request()


def get_polar_data():
    scope = 'accesslink.read_all'
    myState = 'myState'
    # response = requests.get(url='https://flow.polar.com/oauth2/authorization?response_type=code&scope='+scope+'&client_id='+client_id_polar+'&state='+myState)
    # print(response)

    polar_accesslink = AccessLink(client_id=client_id_polar,
                                 client_secret=client_secret_polar,
                                 redirect_url='http://localhost/')

    # Navigate the user to the following URL, so they can complete the authorization form.
    # Code for this will vary by application.
    auth_url = polar_accesslink.get_authorization_url()
    driver = webdriver.Chrome()  # open the browser

    # Go to the correct domain
    driver.get(auth_url)

    # Now set the cookie. Here's one for the entire domain
    # the cookie name here is 'key' and it's value is 'value'
    # additional keys that can be passed in are:
    # 'domain' -> String,
    # 'secure' -> Boolean,
    # 'expiry' -> Milliseconds since the Epoch it should expire.

    # finally we visit the hidden page
    driver.get('http://www.example.com/secret_page.html')

    # response = requests.get(url=auth_url)
    authorization_code = '659808e260d975920b76151d06323bc3'
    token_response = polar_accesslink.get_access_token(authorization_code)

    user_id = token_response["x_user_id"]
    access_token = token_response["access_token"]

    try:
        polar_accesslink.users.register(access_token=access_token)
    except requests.exceptions.HTTPError as err:
        # Error 409 Conflict means that the user has already been registered for this client.
        # For most applications, that error can be ignored.
        if err.response.status_code != 409:
            raise err
        user_info = polar_accesslink.users.get_information(user_id=user_id,
                                                          access_token=access_token)
        daily_activity_transaction = polar_accesslink.daily_activity.create_transaction(user_id=user_id,
                                                                                       access_token=access_token)
        daily_activity_response = requests.get(url=daily_activity_transaction.transaction_url,
                                               headers={'Accept': 'application/json',
                                                        'Authorization': 'Bearer ' + access_token})
        json.loads(daily_activity_response.text).get('activity-log')
        print(user_info)
    pass


def cacca():
    global polarAccessLink
    creds = get_credentials(token_file='token.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
    file_name = 'credentials/spreadSheetId.json'
    key_name = 'SPREADSHEET_ID'
    value_input_option = 'USER_ENTERED'
    try:
        lastRow = get_last_row(service=build('sheets', 'v4', credentials=creds), file_name=file_name, key_name=key_name)

        numberOfDays = 10
        date = get_last_date(service=build('sheets', 'v4', credentials=creds), fileName=file_name, keyName=key_name)
        arrayOfDates = get_array_of_dates(last_date=date, number_of_days=numberOfDays)
        yesNoTrainingValues = ['Test'] * numberOfDays
        training_feeling_values = ['Test'] * numberOfDays
        generalFeelingValues = ['Test'] * numberOfDays
        weightValues = ['Test'] * numberOfDays
        noteValues = ['Test'] * numberOfDays

        # doShitWithPolarAndStrava()
        # addGui()
        polarData = get_polar_data()

        sleepingQualities = ['Test'] * numberOfDays
        sleepingTimes = ['Test'] * numberOfDays
        energyConsumptions = ['Test'] * numberOfDays
        averageHeartBeatFrequencies = ['Test'] * numberOfDays
        steps = ['Test'] * numberOfDays
        measuredKms = ['Test'] * numberOfDays
        shoes = ['Test'] * numberOfDays

        df = get_data_frame_from_values(dates=arrayOfDates, yes_no_training_values=yesNoTrainingValues,
                                        training_feeling_values=training_feeling_values,
                                        general_feeling_values=generalFeelingValues, weight_values=weightValues,
                                        note_values=noteValues)
        body = {
            'values': df.values.tolist()
        }
        rangeToWrite = ('A' + str(lastRow + 1) + ':F' + str(lastRow + numberOfDays))
        write_values_in_range(service=build('sheets', 'v4', credentials=creds), file_name=file_name, key_name=key_name,
                              rangee=rangeToWrite, value_input_option=value_input_option, body=body)
    except HttpError as err:
        print(err)

if __name__ == "__main__":
    username = "ferocemarcello@gmail.com"
    password = ""
    garmin_object = garmin_utils.GarminUtils(username=username,password=password)
    garmin_object.get_data()
