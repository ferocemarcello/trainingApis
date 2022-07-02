from __future__ import print_function

import json
import os.path
import webbrowser
from datetime import timedelta

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

client_id_google = '288512384213-h737qune0i8k8i13p49sb73taa20l810.apps.googleusercontent.com'
client_secret_google = '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'

client_id_polar = 'ea15e66e-0f27-4faa-8cf2-2928d1262509'
client_secret_polar = '0e1b5074-3436-4d5d-b286-ae4d1fe2f83c'

client_id_strava = '84341'
client_secret_strava = 'd982e50eb5253a32dd7665a4400be9bbd2bf7dfc'
access_token_strava = 'de5a54102f1c72cea5ec504632997c0f2a9559dd'
refresh_token_strava = 'f61e3ebe8bc18b00b16556dc52f0c1505f3450d2'

base64encondedClientIdSecret = 'ZWExNWU2NmUtMGYyNy00ZmFhLThjZjItMjkyOGQxMjYyNTA5OjBlMWI1MDc0LTM0MzYtNGQ1ZC1iMjg2LWFlNGQxZmUyZjgzYw=='


def getDataFromSpreadsheet(service, fileName, keyName, range):
    return service.spreadsheets().values().get(spreadsheetId=getSpreadSheetId(fileName=fileName, keyName=keyName),
                                range=range).execute()


def getLastRow(service, fileName='spreadSheetId.json', keyName='SPREADSHEET_ID'):
    all_range = 'A1:F'
    result = getDataFromSpreadsheet(service=service,fileName=fileName, keyName=keyName, range=all_range)
    return len(result.get('values'))

def getLastDate(service, fileName='spreadSheetId.json', keyName='SPREADSHEET_ID'):
    date_range = 'A1:A'
    result = getDataFromSpreadsheet(service=service,fileName=fileName, keyName=keyName, range=date_range)
    return result.get('values')[len(result.get('values')) - 1][0]

def incrementDateByNumberOfDays(date_time_str='01∕01/2000', numberOfDays=1):
    from datetime import datetime
    date_time_obj = datetime.strptime(date_time_str +' 00:00:00', '%d/%m/%Y %H:%M:%S')
    date_time_obj += timedelta(days=numberOfDays)
    return date_time_obj.strftime("%d/%m/%Y")

def getArrayOfDates(lastDate,numberOfDays):
    dateArray=[]
    for dayIncrement in range(1,numberOfDays+1):
        dateArray.append(incrementDateByNumberOfDays(date_time_str=lastDate,numberOfDays=dayIncrement))
    return dateArray

def getSpreadSheetId(fileName='spreadSheetId.json', keyName='SPREADSHEET_ID'):
    with open(fileName) as f:
        data = json.load(f)
    f.close()
    return data.get(keyName)

# If modifying these scopes, delete the file token.json.
def getCredentials(tokenFile='token.json', SCOPES=['https://www.googleapis.com/auth/spreadsheets']):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenFile):
        creds = Credentials.from_authorized_user_file(tokenFile, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(tokenFile, 'w') as token:
            token.write(creds.to_json())
    return creds


def writeValuesInRange(service, fileName, keyName, range, value_input_option, body):
    result = service.spreadsheets().values().update(
        spreadsheetId=getSpreadSheetId(fileName=fileName,keyName=keyName), range=range,
        valueInputOption=value_input_option, body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))


def getDataFrameFromValues(dates, yesNoTrainingValues, trainingFeelingValues, generalFeelingValues, weightValues,
                           noteValues):
    import pandas as pd
    df = pd.DataFrame()
    dateDataFrame = pd.DataFrame({
        'Date': dates
    })
    generalDataFrame = pd.DataFrame({
        'Training_yes_no': yesNoTrainingValues,
        'Training_feeling': trainingFeelingValues,
        'General_feeling': generalFeelingValues,
        'Weight': weightValues,
        'Notes': weightValues
    })
    df['Date'] = dateDataFrame
    df['Training_yes_no'] = generalDataFrame['Training_yes_no']
    df['Training_feeling'] = generalDataFrame['Training_yes_no']
    df['General_feeling'] = generalDataFrame['General_feeling']
    df['Weight'] = generalDataFrame['Weight']
    df['Notes'] = generalDataFrame['Notes']

    return df

def getPolarOauthCode(client_id_polar, client_secret_polar):
    import requests
    import webbrowser
    requestUrl = 'https://flow.polar.com/oauth2/authorization?response_type=code&scope=accesslink.read_all&client_id='+client_id_polar
    #result = requests.get(requestUrl)
    #resp = webbrowser.open(requestUrl)
    return requestUrl


def getPolarAccessToken(oauthCode):
    requestUrl = 'https://polarremote.com/v2/oauth2/token'
    headers = {"Authorization":"Basic ea15e66e-0f27-4faa-8cf2-2928d1262509:0e1b5074-3436-4d5d-b286-ae4d1fe2f83c"}
    body = { "grant_type":"authorization_code","code":oauthCode }
    result = requests.post(requestUrl,headers=headers, json=body)
    return result


def doShitWithPolarAndStrava():
    oauthCodePolar = getPolarOauthCode(client_id_polar=client_id_polar, client_secret_polar=client_secret_polar)
    oauthCodePolar = '97e6e13bcc23f5160509d2af10769ae6'
    polarAccessToken = getPolarAccessToken(oauthCode=oauthCodePolar)

    headers = {"Authorization": "Bearer de5a54102f1c72cea5ec504632997c0f2a9559dd"}

    result = requests.get('https://www.strava.com/api/v3/athlete',headers=headers)

    from bs4 import BeautifulSoup
    import re
    from urllib.parse import unquote

    url = 'http://www.strava.com/oauth/authorize?client_id='+client_id_strava+'&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=read'
    response = requests.get(url, verify=False, allow_redirects=True)

    if response.status_code == 200:
        page = response.text
        # parse the html using beautifulsoup
        html_content = BeautifulSoup(page, 'html.parser')
        soup = html_content
        href = soup.find("link", href=True)
        href = href['href']

        new_url = unquote(unquote(href))

    result = webbrowser.open('http://www.strava.com/oauth/authorize?client_id='+client_id_strava+'&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=read')


def addGui():
    import tkinter as tk
    window = tk.Tk()

    entry = tk.Entry(width=40, bg="white", fg="black")
    entry.pack()

    entry.insert(0, "What is your name?")

    window.mainloop()
    print("")

import http.server
# replace with your own http handlers
def wait_for_request(server_class=http.server,
                     handler_class=http.server.BaseHTTPRequestHandler):
    server_address = ('', 5000)
    httpd = server_class.HTTPServer(server_address=server_address,RequestHandlerClass=handler_class)
    return httpd.handle_request()

def getPolarData():
    scope = 'accesslink.read_all'
    myState = 'myState'
    #response = requests.get(url='https://flow.polar.com/oauth2/authorization?response_type=code&scope='+scope+'&client_id='+client_id_polar+'&state='+myState)
    #print(response)

    from accesslink import AccessLink

    polarAccesslink = AccessLink(client_id=client_id_polar,
                                 client_secret=client_secret_polar,
                                 redirect_url='http://localhost/')


    # Navigate the user to the following URL so they can complete the authorization form.
    # Code for this will vary by application.
    auth_url = polarAccesslink.get_authorization_url()

    from selenium import webdriver
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

    #response = requests.get(url=auth_url)
    authorization_code = '659808e260d975920b76151d06323bc3'
    token_response = polarAccesslink.get_access_token(authorization_code)

    USER_ID = token_response["x_user_id"]
    ACCESS_TOKEN = token_response["access_token"]

    try:
        polarAccesslink.users.register(access_token=ACCESS_TOKEN)
    except requests.exceptions.HTTPError as err:
        # Error 409 Conflict means that the user has already been registered for this client.
        # For most applications, that error can be ignored.
        if err.response.status_code != 409:
            raise err
        user_info = polarAccesslink.users.get_information(user_id=USER_ID,
                                                          access_token=ACCESS_TOKEN)
        daily_activity_transaction = polarAccesslink.daily_activity.create_transaction(user_id=USER_ID,
                                                                                       access_token=ACCESS_TOKEN)
        daily_activity_response = requests.get(url=daily_activity_transaction.transaction_url,
                     headers={'Accept': 'application/json', 'Authorization': 'Bearer ' + ACCESS_TOKEN})
        json.loads(daily_activity_response.text).get('activity-log')
        print(user_info)
    pass


def cacca():
    global polarAccessLink
    creds = getCredentials(tokenFile='token.json',SCOPES=['https://www.googleapis.com/auth/spreadsheets'])
    fileName = 'credentials/spreadSheetId.json'
    keyName = 'SPREADSHEET_ID'
    value_input_option = 'USER_ENTERED'
    try:
        lastRow = getLastRow(service = build('sheets', 'v4', credentials=creds), fileName=fileName, keyName=keyName)

        numberOfDays = 10
        date = getLastDate(service = build('sheets', 'v4', credentials=creds), fileName=fileName, keyName=keyName)
        arrayOfDates = getArrayOfDates(lastDate=date,numberOfDays=numberOfDays)
        yesNoTrainingValues = ['Test']*numberOfDays
        trainingFeelingValues = ['Test']*numberOfDays
        generalFeelingValues = ['Test']*numberOfDays
        weightValues = ['Test']*numberOfDays
        noteValues = ['Test']*numberOfDays

        #doShitWithPolarAndStrava()
        #addGui()
        polarData = getPolarData()

        sleepingQualities=['Test'] * numberOfDays
        sleepingTimes = ['Test'] * numberOfDays
        energyConsumptions = ['Test'] * numberOfDays
        averageHeartBeatFrequencies = ['Test'] * numberOfDays
        steps = ['Test'] * numberOfDays
        measuredKms = ['Test'] * numberOfDays
        shoes = ['Test'] * numberOfDays

        df = getDataFrameFromValues(dates=arrayOfDates,yesNoTrainingValues=yesNoTrainingValues, trainingFeelingValues=trainingFeelingValues, generalFeelingValues=generalFeelingValues, weightValues=weightValues,noteValues=noteValues)
        body = {
            'values': df.values.tolist()
        }
        rangeToWrite=('A'+str(lastRow+1)+':F'+str(lastRow+numberOfDays))
        writeValuesInRange(service = build('sheets', 'v4', credentials=creds), fileName=fileName, keyName=keyName, range=rangeToWrite, value_input_option=value_input_option, body=body)
    except HttpError as err:
        print(err)