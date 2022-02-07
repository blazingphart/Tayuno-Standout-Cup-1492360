import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import requests
import time
import os
from collections import OrderedDict


API_URL = 'https://osu.ppy.sh/api'
TOKEN_URL = 'https://osu.ppy.sh/oauth/token'


def get_token(client_id, client_secret):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'public'
    }

    response = requests.post(TOKEN_URL, data=data)

    return response.json().get('access_token')


def get_max_combo(beatmap_id, token, key):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }
    params = {
        'k' : key,
        'm': 0,
        'b': beatmap_id
    }
    beatmap_info = requests.get(f'{API_URL}/get_beatmaps', params=params, headers=headers)

    return beatmap_info.json()[0]['max_combo']


def create_pool(round, client_id, client_secret, spreadsheet_id, key):
    sheet_name = "Tayuno mappool"
    print("Mod column:")
    mod_col = str(input()).upper()
    print("Starting row:")
    start_row = str(input())
    print("Beatmap id column:")
    id_col = str(input())
    print("Ending row:")
    end_row = str(input()).upper()
    range_name = "{}!{}{}:{}{}".format(sheet_name, mod_col, start_row, id_col, end_row)

    creds = None

    with open('creds.json', 'r') as f:
        creds = json.load(f)
    f.close()

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scopes=['https://www.googleapis.com/auth/spreadsheets'])

    service = build('sheets', 'v4', credentials=credentials)

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    data = result.get('values', [])
    pool = OrderedDict()
    for row in data:
        mod = row[0]
        map_id = row[-1]
        max_combo = get_max_combo(map_id, get_token(client_id, client_secret), key)
        pool[mod] = {"id": map_id, "max_combo": max_combo}
        print("Mod: {} | Beatmap id: {} | Max combo: {}".format(mod, map_id, max_combo))
        time.sleep(1.5)

    old_pool = {}
    with open('pool.json', 'r') as f:
        old_pool = json.load(f)
    f.close()

    old_pool[round] = pool

    with open('pool.json', 'w') as f:
        json.dump(old_pool, f, indent=4)
    f.close()



def main():
    load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    key = os.getenv("KEY")
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    print("Round:")
    round = str(input())
    create_pool(round, client_id, client_secret, spreadsheet_id, key)


if __name__ == '__main__':
    main()

