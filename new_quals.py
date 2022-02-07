import datetime
import time
import json
from typing import final
from dotenv import load_dotenv
import requests
import pprint
import os

API_URL = 'https://osu.ppy.sh/api'
TOKEN_URL = 'https://osu.ppy.sh/oauth/token'


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

def read_quals_result():
    with open('new_quals.json', 'r') as f:
        quals_result = json.load(f)
    f.close()
    return quals_result


def save_quals_result(quals_result):
    with open('new_quals.json', 'w') as f:
        json.dump(quals_result, f, indent=4)
    f.close()


def add_result(current_mp, new_mp):
    for map in new_mp:
        for user_id in new_mp[map]:
            current_mp[map][user_id] = new_mp[map][user_id]
    return current_mp


def get_token(client_id, client_secret):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'public'
    }

    response = requests.post(TOKEN_URL, data=data)

    return response.json().get('access_token')


def calculate_acc(n300, n100, n50, nmiss):
    n300 = int(n300)
    n100 = int(n100)
    n50 = int(n50)
    nmiss = int(nmiss)

    acc = (300*n300 + 100*n100 + 50*n50) / (300*(n300 + n100 + n50 + nmiss))
    acc = round(acc, 4)*100.0
    return acc


def get_pool():
    with open('pool.json', 'r') as f:
        pool = json.load(f)
    f.close()
    return pool


def process_mp(mp, pool):
    players = {}
    with open("players.json", "r") as f:
        players = json.load(f)
    f.close()

    pool_value = list(pool.values())
    mappool_id = []
    for i in range(len(pool_value)):
        mappool_id.append(pool_value[i]['id'])

    first_run = {}
    with open("team_scores_first_run.json", "r") as f:
        first_run = json.load(f)
    f.close()

    second_run = {}
    with open("team_scores_second_run.json", "r") as f:
        second_run = json.load(f)
    f.close()
    
    for i in range(len(mp)):
        if i < 10:
            map_id = mp[i]['beatmap_id']
            if map_id in mappool_id:
                for score in mp[i]['scores']:
                    player_id = score['user_id']
                    try:
                        team_name = players[player_id]
                    except KeyError:
                        print("User id: {} does not exsit in teams.json".format(player_id))
                    else:
                        first_run[team_name][map_id][player_id] = {"score": int(score["score"]), 
                                        "acc": float('%.2f' % round(calculate_acc(score["count300"], score["count100"], score["count50"], score["countmiss"]), 2)),
                                        "combo": int(score["maxcombo"])
                                        }
                        first_run[team_name][map_id]["Team score"] += int(score["score"])
        else:
            map_id = mp[i]['beatmap_id']
            if map_id in mappool_id:
                for score in mp[i]['scores']:
                    player_id = score['user_id']
                    try:
                        team_name = players[player_id]
                    except KeyError:
                        print("User id: {} does not exsit in teams.json".format(player_id))
                    else:
                        second_run[team_name][map_id][player_id] = {"score": int(score["score"]), 
                                        "acc": float('%.2f' % round(calculate_acc(score["count300"], score["count100"], score["count50"], score["countmiss"]), 2)),
                                        "combo": int(score["maxcombo"])
                                        }
                        second_run[team_name][map_id]["Team score"] += int(score["score"])
        
        with open("team_scores_first_run.json", "w") as f:
            json.dump(first_run, f, indent=4)
        f.close()

        with open("team_scores_second_run.json", "w") as f:
            json.dump(second_run, f, indent=4)
        f.close()


def download_data(pool, client_id, client_secret, key):
    quals_lobby = []

    with open("quals_lobby.json", "r") as f:
        quals_lobby = json.load(f)
    f.close()

    for i in range(len(quals_lobby)):
        link = str(quals_lobby[i])
        print("{}:{}:{} / {}:{} / {}".format(datetime.datetime.now().hour, datetime.datetime.now().minute, datetime.datetime.now().second, i+1, len(quals_lobby), link))
        process_mp(fetch_scores_from_mp(link, get_token(client_id, client_secret), key), pool)


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

    return maps_played


def final_team_score():
    first_run = {}
    with open("team_scores_first_run.json", "r") as f:
        first_run = json.load(f)
    f.close()

    second_run = {}
    with open("team_scores_second_run.json", "r") as f:
        second_run = json.load(f)
    f.close()

    final_score = {}
    with open("final_team_score.json", "r") as f:
        final_score = json.load(f)
    f.close()

    for team_name in final_score:
        for map_id in final_score[team_name]:
            if first_run[team_name][map_id]["Team score"] > second_run[team_name][map_id]["Team score"]:
                for label in first_run[team_name][map_id]:
                    final_score[team_name][map_id][label] = first_run[team_name][map_id][label]   
            else:
                for label in second_run[team_name][map_id]:
                    final_score[team_name][map_id][label] = second_run[team_name][map_id][label]

            diff = first_run[team_name][map_id]["Team score"] - second_run[team_name][map_id]["Team score"]

            if diff > 0:
                final_score[team_name][map_id]["Run"] = "First"
            else: 
                final_score[team_name][map_id]["Run"] = "Second"
            final_score[team_name][map_id]["Difference"] = abs(diff)

    with open("final_team_score.json", "w") as f:
        json.dump(final_score, f, indent=4)
    f.close()



def main():
    pool = get_pool()
    load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    key = os.getenv("KEY")
    download_data(pool, client_id, client_secret, key)
    final_team_score()


if __name__ == '__main__':
    main()