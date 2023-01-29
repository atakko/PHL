from requests import Response, get, exceptions
from typing import Union

NHL_API_URL = 'https://statsapi.web.nhl.com/api/v1/'

def _get(path: str):
    resp = get(NHL_API_URL + path)
    return resp.json()


def getTeams():
    json = _get('teams')
    return json['teams']

def getTeam(team:Union[int, str]):
    teams_data = getTeams()
    if isinstance(team, int):
        return list(filter(lambda x: x['id'] == team, teams_data))[0]
    else:
        name = team.lower()
        return list(filter(
            lambda team: name in [x.lower() for x in [team['name'], team['teamName'], team['abbreviation']]],
            teams_data))[0]

def getPlayers(team:Union[int, str]):
    team = getTeam(team)
    players = _get(f'teams/{team["id"]}/roster')
    return players['roster']

def getPlayers2(team:Union[int, str]):
    team = getTeam(team)
    players = _get(f'teams/{team["id"]}/roster?expand=team.roster&season=20222023')
    return players['roster']

def getPlayer(id:int):
    # json = _get(f'people/{id}&season=20222023')
    json = _get(f'people/{id}')
    return json['people'][0]

def getPlayerStats(id:int, season):
    # json = _get(f'people/{id}&season=20222023')
    json = _get(f'people/{id}/stats?stats=statsSingleSeason&season={season}')
    return json


def getFins():
    fins = []
    for x in range(8471130, 8500000):
        data = getPlayer(x)
        if not 'people' in data:
            print(f'{x} not found')
            # break
            continue

        player = data["people"][0]
        if not 'nationality' in player:   
            print(f'No nationality: {player}')
            continue

        if player['nationality'] == 'FIN':
            print(f'FIN: {player}')
            print(f'{x}: {player["birthDate"]} {player["fullName"]}')
        

