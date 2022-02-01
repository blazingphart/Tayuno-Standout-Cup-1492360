from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import json
from dotenv import load_dotenv
import os
import pprint
from collections import defaultdict


def import_players(spreadsheet_id, service, range_name):

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    data = result.get('values', [])

    players = {}

    for team in data:
        team_name = team[0]
        for i in range(5, 9, 1):
            player_id = team[i].split("https://osu.ppy.sh/users/")[1]
            players[player_id] = team_name

    with open("players.json", "w") as f:
        json.dump(players, f, indent=4)
    f.close()


def make_blank_team_score():
    players = {}
    with open("players.json", "r") as f:
        players = json.load(f)
    f.close()

    mappool_id = []
    pool = {}
    with open("pool.json", "r") as f:
        pool = json.load(f)
    f.close()
    
    for mod in pool:
        mappool_id.append(pool[mod]['id'])

    teams = dict.fromkeys(list(players.values()), dict.fromkeys(mappool_id, {}))

    for player_id in list(players.keys()):
        team_name = players[player_id]
        for beatmap_id in teams[team_name]:
            teams[team_name][beatmap_id][player_id] = 0

    pprint.pprint(teams, indent=4)
        

def main():
    load_dotenv()

    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    CREDS = None

    with open('creds.json', 'r') as f:
        CREDS = json.load(f)
    f.close()

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(CREDS, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=credentials)
    tayuno_range = os.getenv("TAYUNO_RANGE")

    import_players(spreadsheet_id, service, tayuno_range)
    make_blank_team_score()

if __name__ == '__main__':
    main()
