import json
from json import JSONDecodeError

import isodate as isodate
import requests
from flask import Flask, request, redirect

import vesync

CALLBACK_ENDPOINT = "/oauth2_callback"
CALLBACK_PORT = 5000
REDIRECT_URL = "http://localhost:{}{}".format(CALLBACK_PORT, CALLBACK_ENDPOINT)


def get_polar_credentials(filename):
    with open(filename) as f:
        data = json.load(f)
    f.close()
    return data


app = Flask(__name__)


def register_user(config_dict):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + config_dict["access_token"]
    }
    body = {"member-id": config_dict["user_id"]}
    return requests.post('https://www.polaraccesslink.com/v3/users', headers=headers, json=body)


def get_user_info(config_dict):
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + config_dict["access_token"]
    }

    return requests.get('https://www.polaraccesslink.com/v3/users/' + str(config_dict["user_id"]),
                        headers=headers).json()


def get_id_from_url(url):
    return url.split("/")[len(url.split("/")) - 1]


def get_all_activities(config_dict):
    activities = {}
    activity_urls = []
    passed = False
    while passed is False:
        try:
            activity_urls = make_transactions_get_urls(config_dict=config_dict, data_name='activity-transactions')
            passed = True
        except JSONDecodeError:
            pass
    for activity_url in activity_urls:
        activities[get_id_from_url(activity_url)] = get_activity_training_summary(url=activity_url,
                                                                                  config_dict=config_dict)
    return activities


def get_all_activities_or_training(config_dict, data_name):
    data_list = {}
    data_urls = []
    passed = False
    while passed is False:
        try:
            data_urls = make_transactions_get_urls(config_dict=config_dict, data_name=data_name)
            passed = True
        except JSONDecodeError:
            pass
    for url in data_urls:
        data_list[get_id_from_url(url)] = get_activity_training_summary(url=url, config_dict=config_dict)
    return data_list


@app.route("/")
def authorize():
    scope = 'accesslink.read_all'
    client_id = config['client_id']
    redirect_uri = REDIRECT_URL
    auth_url = 'https://flow.polar.com/oauth2/authorization?response_type=code&scope=' + scope + '&client_id=' + \
               client_id + '&redirect_uri=' + redirect_uri
    return redirect(auth_url)


def save_polar_credentials(config_dict, filename):
    pass


@app.route(CALLBACK_ENDPOINT)
def callback():
    authorization_code = request.args.get("code")
    import base64
    base64encoding = base64.b64encode((config['client_id'] + ':' + config['client_secret']).encode('ascii')).decode(
        "utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json;charset=UTF-8",
        "Authorization": "Basic " + base64encoding
    }
    data = {"grant_type": "authorization_code", "code": authorization_code, "redirect_uri": REDIRECT_URL}
    token_response = requests.post(url='https://polarremote.com/v2/oauth2/token', headers=headers, data=data)
    config["user_id"] = token_response.json()["x_user_id"]
    config["access_token"] = token_response.json()['access_token']
    save_polar_credentials(config_dict=config, filename=CONFIG_FILENAME)
    shutdown()
    return "Client authorized! You can now close this page."


def shutdown():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is not None:
        shutdown_func()


def authorization_session(port):
    print("Navigate to http://localhost:{port}/ for authorization.\n".format(port=port))
    app.run(host='localhost', port=port)


def make_transactions_get_urls(config_dict, data_name):
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + config_dict["access_token"]
    }

    user_transaction_response = requests.post('https://www.polaraccesslink.com/v3/users/' + str(
        config_dict["user_id"]) + '/' + data_name, params={}, headers=headers)
    transaction_id = user_transaction_response.json()['transaction-id']
    log = requests.get('https://www.polaraccesslink.com/v3/users/' + str(
        config_dict["user_id"]) + '/' + data_name + '/' + str(transaction_id), params={},
                       headers=headers).json()
    if data_name == 'activity-transactions':
        return log['activity-log']
    if data_name == 'exercise-transactions':
        return log['exercises']


def get_activity_training_summary(url, config_dict):
    headers = {
        'Accept': 'application/json',
        "Authorization": "Bearer " + config_dict["access_token"]
    }
    response = requests.get(url=url, params={}, headers=headers).json()
    response['duration'] = str(isodate.parse_duration(response['duration']))
    return response


def get_all_trainings(config_dict):
    trainings = {}
    training_urls = []
    passed = False
    while passed is False:
        try:
            training_urls = make_transactions_get_urls(config_dict=config_dict, data_name='exercise-transactions')
            passed = True
        except JSONDecodeError:
            pass
    for training_url in training_urls:
        trainings[get_id_from_url(training_url)] = get_activity_training_summary(url=training_url,
                                                                                 config_dict=config_dict)
    return trainings


def get_all_nights(config_dict):
    import requests
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+config_dict["access_token"]
    }
    response = requests.get('https://www.polaraccesslink.com/v3/users/sleep', params={}, headers=headers)
    return response.json()['nights']


if __name__ == "__main__":
    data_scale = vesync.get_data()
    print("vesync: " + data_scale())
    print("ff")
    CONFIG_FILENAME = "credentials/config_polar.json"
    config = get_polar_credentials(filename=CONFIG_FILENAME)
    while "access_token" not in config:
        print("Authorization is required. Run authorization.py first.")
        authorization_session(port=CALLBACK_PORT)
        config = get_polar_credentials(filename=CONFIG_FILENAME)
    user_info = get_user_info(config_dict=config)
    print(user_info)
    user_nights = get_all_nights(config_dict=config)
    user_activities = get_all_activities_or_training(config_dict=config, data_name='activity-transactions')
    user_trainings = get_all_activities_or_training(config_dict=config, data_name='exercise-transactions')
    print(user_activities)
