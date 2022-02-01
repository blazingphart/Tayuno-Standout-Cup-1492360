import collections
import requests
import json
import time
import datetime
import pycountry
from dotenv import load_dotenv
import os

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

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


def look_up_userid(username, token, key):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }
    params = {
        'k' : key,
        'u': str(username),
        'm': 0
    }
    user = requests.get(f'{API_URL}/get_user', params=params, headers=headers)
    try:
        userid = user.json()[0]['user_id']
    except IndexError:
        print("Invalid username")
    else:
        print(userid) 


def get_user(id, token, key):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }
    params = {
        'k' : key,
        'u': id,
        'm': 0
    }
    user = requests.get(f'{API_URL}/get_user', params=params, headers=headers)
    return user.json()


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


def fetch_scores_from_mp(mp_link, token, key):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }
    room = mp_link.split('/')[-1]
    params = {
        'k' : key,
        'mp' : room,
    }
    match = requests.get(f'{API_URL}/get_match', params=params, headers=headers)
    maps_played = (match.json()['games'])
    mp_history = {}
    beatmap_ids = []
    for i in range(len(maps_played)):
        beatmap_ids.append(maps_played[i]['beatmap_id'])
        mp_history[maps_played[i]['beatmap_id']] = maps_played[i]['scores']

    return mp_history


def calculate_acc(n300, n100, n50, nmiss):
    n300 = int(n300)
    n100 = int(n100)
    n50 = int(n50)
    nmiss = int(nmiss)

    acc = (300*n300 + 100*n100 + 50*n50) / (300*(n300 + n100 + n50 + nmiss))
    acc = round(acc, 4)*100.0
    return acc


def process_mp(mp, pool):
    result = {}
    pool_value = list(pool.values())
    mappool_id = []
    for i in range(len(pool_value)):
        mappool_id.append(pool_value[i]['id'])

    for map in mp:
        try:
            valid = map in mappool_id
            if valid == False:
                raise ValueError
        except ValueError:
            print("Beatmap id {} is not in the pool".format(map))
        else:
            result[map] = {}
            for score in mp[map]:
                user_id = score["user_id"]            
                result[map][user_id] = {"score": int(score["score"]), 
                                        "acc": float('%.2f' % round(calculate_acc(score["count300"], score["count100"], score["count50"], score["countmiss"]), 2)),
                                        "combo": int(score["maxcombo"])
                                        }
    return result


def add_result(current_mp, new_mp):
    for map in new_mp:
        for user_id in new_mp[map]:
            current_mp[map][user_id] = new_mp[map][user_id]
    return current_mp


def save_quals_result(quals_result):
    with open('qualifiers.json', 'w') as f:
        json.dump(quals_result, f, indent=4)
    f.close()


def read_quals_result():
    with open('qualifiers.json', 'r') as f:
        quals_result = json.load(f)
    f.close()
    return quals_result


def get_all_scores(quals_result, map_id, sort):
    scores = []
    map_id = str(map_id)
    for user_id in quals_result[map_id]:
        scores.append(quals_result[map_id][user_id]["score"])

    if sort == "A":
        ascending_scores = scores.copy()
        ascending_scores.sort()
        return scores, ascending_scores
    elif sort == "D":
        descening_scores = scores.copy()
        descening_scores.sort(reverse=True)
        return scores, descening_scores
    
    return scores, []


def get_players_leaderboard(quals_result, top, map_id, mod, client_id, client_secret, key):
    unsorted_score, sorted_score = get_all_scores(quals_result, map_id, "D")
    user_id_list = list(quals_result[map_id].keys())
    pool = None
    with open("pool.json", "r") as f:
        pool = json.load(f)
    f.close()

    teams = {}
    with open("players.json", "r") as f:
        teams = json.load(f)
    f.close()
    
    mod = mod.upper()
    max_combo = pool[mod]["max_combo"]

    for i in range(int(top)):
        try:
            score = sorted_score[i]
            index = unsorted_score.index(score)
            user_id = user_id_list[index]
            acc = quals_result[map_id][user_id]['acc']
            combo = quals_result[map_id][user_id]['combo']
            user = get_user(int(user_id), get_token(client_id, client_secret), key)[0]
            print("{}. Score: {} | Accuracy: {} | Combo: {}/{} | Username: {} | Team: {} | PP: {} | Country: {}".format(i+1, score, acc, combo, max_combo, user['username'], teams[user_id], user['pp_raw'], pycountry.countries.get(alpha_2=user['country']).name))
            time.sleep(1.5)
        except KeyError:
            print("What the fuck player not found????")
        
    
    
def get_all_scores_of_player(quals_result, user_id, pool):
    user_id = str(user_id)
    maps_played = list(quals_result.keys())
    info = collections.OrderedDict()
    for map_id in maps_played:
        scores, sorted_scores = get_all_scores(quals_result, map_id=map_id, sort="D")
        try:
            player_score = quals_result[map_id][user_id]["score"]
        except KeyError:
            info.update({map_id: {"score": 0, "ranking": "{}/{}".format(0, len(quals_result[map_id]))}})
            # info[map_id] = {"score": 0, "ranking": "Did not play"}
        else:
            info.update({map_id: {"score": player_score, "ranking": "{}/{}".format(sorted_scores.index(player_score) + 1, len(quals_result[map_id]))}})
            # info[map_id] = {"score": player_score, "ranking": sorted_scores.index(player_score) + 1}
    
    print("User: {}".format(user_id))
    for map in info:
        mod = beatmap_id_to_mod(map, pool)
        print("Mod: {} | Score: {} | Combo: {}/{} | Ranking: {}".format(mod, info[map]['score'], quals_result[map][user_id]["combo"], pool[mod]["max_combo"], info[map]['ranking']))


def beatmap_id_to_mod(beatmap_id, pool):
    pool_value = list(pool.values())
    for i in range(len(pool_value)):
        if beatmap_id == pool_value[i]['id']:
            return list(pool.keys())[i]

    return "No beatmap id found"


def mod_to_beatmap_id(mod, pool):
    try: 
        mod.upper()
    except:
        return "No mod found"
    else:
        return pool["{}".format(mod.upper())]["id"]


def create_pool(mode, nm, hd, hr, dt, fm, tb, client_id, client_secret, spreadsheet_id, key):
    pool_with_beatmap_id = {}
    mods = {"NM": nm,
            "HD": hd,
            "HR": hr,
            "DT": dt,
            "FM": fm,
            "TB": tb}
            
    match mode:
        case "1":
            print("Please enter pool's beatmap id one by one")
            for mod in mods:
                for mod_num in range(mods[mod]):
                    print("{}{}".format(mod, mod_num + 1))
                    id = str(input())
                    pool_with_beatmap_id["{}{}".format(mod, mod_num + 1)] = {"id": id, "max_combo": get_max_combo(id, get_token(client_id, client_secret), key)}
        
        case "2":
            print("Sheet name:")
            sheet_name = str(input())
            print("Column:")
            col = str(input())
            print("Starting row:")
            start_row = str(input())
            print("Ending row:")
            end_row = str(input())
            range_name = "{}!{}{}:{}{}".format(sheet_name, col, start_row, col, end_row)

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

            count = 0

            for mod in mods:
                for mod_num in range(mods[mod]):
                    id = data[count][0]
                    max_combo = get_max_combo(id, get_token(client_id, client_secret), key)
                    pool_with_beatmap_id["{}{}".format(mod, mod_num + 1)] = {"id": id, "max_combo": max_combo}
                    count += 1
                    print("{}{}, max combo: {}".format(mod, mod_num + 1, max_combo))
                    time.sleep(1.5)

    
    with open('pool.json', 'w') as f:
        json.dump(pool_with_beatmap_id, f, indent=4)
    f.close()


def get_pool():
    with open('pool.json', 'r') as f:
        pool = json.load(f)
    f.close()
    return pool


def listify():
    mp_links = []
    not_done = True
    while not_done:
        print("mp id or mp link:")
        mp = str(input())
        if "matches" in mp:
            mp_links.append(mp)
        else:
            if mp == "0":
                not_done = False
                return mp_links
            elif mp != "":
                mp = "https://osu.ppy.sh/community/matches/" + mp
                mp_links.append(mp)


def download_data(pool, client_id, client_secret, key):
    quals_lobby = listify()
    final_result = read_quals_result()

    for i in range(len(quals_lobby)):
        link = str(quals_lobby[i])
        print("{}:{}:{} / {}:{} / {}".format(datetime.datetime.now().hour, datetime.datetime.now().minute, datetime.datetime.now().second, i+1, len(quals_lobby), link))
        try:
            result = process_mp(fetch_scores_from_mp(link, get_token(client_id, client_secret), key), pool)
        except:
            print("Something is wrong and i dont know why")
        else:
            if len(final_result) == 0:
                final_result = result
            else:
                add_result(final_result, result)
        time.sleep(1.5)
    
    save_quals_result(final_result)

# def make_team_score():
#     individual_scores = {}
#     with open("qualifiers.json", "r") as f:
#         individual_scores = json.load(f)
#     f.close()

#     teams = {}
#     with open("players.json", "r") as f:
#         teams = json.load(f)
#     f.close()

#     pool = {}
#     with open("pool.json" , "r") as f:
#         pool = json.load(f)
#     f.close()

#     team_score = {}
#     for player_id, team_name in teams.items():

    
def main():
    load_dotenv()

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    key = os.getenv("KEY")
    spreadsheet_id = os.getenv("SPREADSHEET_ID")

    quals_result = read_quals_result()
    pool = get_pool()

    instruction = "Mode:\n\
        1: Import quals result\n\
        2: Create pool\n\
        3: Get top n scores on a map\n\
        4: Get all scores and rankings of a player\n\
        5: Look up userid from username"
    print(instruction)
    mode = input()
    match str(mode):
        case "1":
            download_data(pool, client_id, client_secret, key)
            # make_team_score()

        case "2":
            print("1 for manual, 2 for automatic")
            mode = str(input())
            create_pool(mode, 4, 2, 2, 2, 0, 0, client_id, client_secret, spreadsheet_id, key)

        case "3":
            print("Map: (nm1/nm2/etc)")
            mod = str(input())
            map_id = mod_to_beatmap_id(mod, pool)
            print("Top n:")
            n = int(input())
            get_players_leaderboard(quals_result, n, map_id, mod, client_id, client_secret, key)

        case "4":
            print("User id:")
            user_id = int(input())
            get_all_scores_of_player(quals_result, user_id=user_id, pool=pool)

        case "5":
            print("Username:")
            username = str(input())
            look_up_userid(username, get_token(client_id, client_secret), key)


if __name__ == '__main__':
    main()