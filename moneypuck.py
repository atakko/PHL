from typing import List
from enum import Enum
import re
import pandas as pd
from requests import Response, get, exceptions
import utils
import os
import datetime
import shutil

MP_PLAYERS_LOOKUP_URL = "https://moneypuck.com/moneypuck/playerData/playerBios/allPlayersLookup.csv"

MP_ROOT = "./moneypuck/"
MP_PLAYERS_LOOKUP_FILE = "allPlayersLookup.csv"


class UpdateTarget(Enum):
    players = "players"  # Player lookup table
    skaters = "skaters"  # Year specfic skater stats
    goalies = "goalies"  # Year specfic goalies stats

    def __str__(self):
        return self.value


def add_parser(subparsers):
    mp_parser = subparsers.add_parser("mp")

    mp_parser.add_argument(
        "-u",
        "--update",
        type=UpdateTarget,
        dest="update_target",
        nargs='?',
        const=UpdateTarget.skaters,
        help="Download new MoneyPuck files. You can set year (-y) for a specific year, by default current year.",
    )
    mp_parser.add_argument("-y", "--year", nargs='+', type=int, action='store', dest="year", default=utils.current_nhl_year(), help="Target year")
    mp_parser.add_argument("-s", "--situation", type=str, dest="situation", default='all', help="On-ice situation: all, 5on5...")
    mp_parser.add_argument("-n", "--nation", type=str, dest="nation", default='fin', help="Nation, e.g. fin, swe, can...")
    mp_parser.add_argument("-t", "--team", type=str, dest="team", default='all', help="Team, e.g. col, fla, cbj")
    mp_parser.add_argument("-p", "--player", type=int, dest="player", help="Player ID")
    mp_parser.add_argument("-l", "--limit", type=int, dest="limit", help="limit of players")
    mp_parser.add_argument("-c", "--column", type=str, dest="sortColumn", default='points', help="The column rows are sorted by")
    mp_parser.add_argument("-a", "--ascending", type=bool, default=False, dest="sortAscending", help="Sort ascending")
    mp_parser.add_argument("-g", "--group", type=str, dest="groupBy", help="Group by")
    mp_parser.set_defaults(func=mp_command)


def mp_command(args):
    if args.update_target:
        match args.update_target:
            case UpdateTarget.players:
                print('Update players lookup table')
                update_player_lookup()
            case UpdateTarget.skaters:
                print('Update skaters')
                update_skaters(args.year)
            case UpdateTarget.goalies:
                print('Goalies update not implmented')
            case _:
                print(f'Invalid update target: {args.update_target}')
        # Exit
        return

    if (args.player):
        stats = getSkatersStats(args.player, args.year, nationality=args.nation, situation=args.situation)
        with pd.option_context('display.precision', 3):
            print(stats)
    elif args.team != 'all':
        teamStats = getTeamStats(args.year, team=args.team, situation=args.situation)
        with pd.option_context('display.precision', 3):
            print(teamStats)
    else:
        nationStats = getNationStats(args.year, nationality=args.nation, sortColumn=args.sortColumn, situation=args.situation)
        with pd.option_context('display.precision', 3):
            print(nationStats)


def getPlayer(id: int):
    df = pd.read_csv(MP_ROOT + MP_PLAYERS_LOOKUP_FILE, index_col="playerId")
    return df.loc[id]


def getNationPlayers(nationality:str):
    nationality = nationality.upper()
    df = pd.read_csv(MP_ROOT + "allPlayersLookup.csv", index_col="playerId")
    if nationality == 'ALL':
        players = df
        return players
    players = df[df["nationality"] == nationality]
    return players

def getTeamPlayers(team:str):
    team = team.upper()
    df = pd.read_csv(MP_ROOT + "allPlayersLookup.csv", index_col="playerId")
    players = df[df["team"] == team]
    return players

def getRawSkatersStats(year: int):
    df = pd.read_csv(MP_ROOT + f"skaters-{year}.csv", index_col="playerId")
    # for x in list(allStats.columns.values):
    #     print(x)
    return df

def getNationStats(year: int|List[int], nationality:str='fin', sortColumn='points', situation:str='all'):
    players = getNationPlayers(nationality)
    playerIds = players.index.to_list()
    return getSkatersStats(playerIds, year, sortColumn=sortColumn, situation=situation)

def getTeamStats(year: int|List[int], team:str, sortColumn='points', situation:str='all'):
    players = getTeamPlayers(team)
    playerIds = players.index.to_list()
    return getSkatersStats(playerIds, year, sortColumn=sortColumn, situation=situation)


def getSkatersStats(playerIds: int|List[int], years: int|List[int], sortColumn='points', limit=40, situation:str='all'):
    if isinstance(playerIds, int):
        playerIds = [playerIds]
    if isinstance(years, int):
        years = [years]

    sortAscending = False
    multiYear = False

    if len(years) > 1:
        multiYear = True

    rawSkatersStats = getRawSkatersStats(years[0])
    if multiYear:
        for i in range(years[0] + 1, years[1] + 1):
            rawSkatersStats = pd.concat([rawSkatersStats, getRawSkatersStats(i)])
    
    if len(playerIds) == 1:
        # sortColumn = 'I_F_points'
        sortColumn = 'season'

    skatersStats = rawSkatersStats.loc[(rawSkatersStats['situation'] == situation) & rawSkatersStats.index.isin(playerIds)]
    skatersStats = skatersStats[
        [
            'season',
            'name',
            'position',
            'games_played',
            'icetime',
            'onIce_xGoalsPercentage',
            'offIce_xGoalsPercentage',
            'onIce_corsiPercentage',
            'offIce_corsiPercentage',
            'onIce_fenwickPercentage',
            'offIce_fenwickPercentage',
            'iceTimeRank',
            "gameScore",
            "I_F_points",
            "I_F_goals",
            "I_F_primaryAssists",
            "I_F_secondaryAssists",
            "OnIce_F_xGoals",
            "OnIce_F_goals",
            "OnIce_A_xGoals",
            "OnIce_A_goals",
        ]
    ]
    skatersStats["points_per_g"] = skatersStats["I_F_points"] / skatersStats["games_played"]
    skatersStats["points_per_60"] = skatersStats["I_F_points"] / (skatersStats["icetime"] / (60 * 60))
    skatersStats["score_per_60"] = skatersStats["gameScore"] / (skatersStats["icetime"] / (60 * 60))


    total_points = skatersStats["I_F_points"].sum()
    total_score = skatersStats["gameScore"].sum()
    total_games_played = skatersStats["games_played"].sum()
    total_points_per_game = total_points / total_games_played
    total_score_per_game = total_score / total_games_played

    skatersStats['time/g'] = skatersStats['icetime'] / skatersStats["games_played"]
    skatersStats['time/g'] = skatersStats['time/g'].apply(lambda x: formatToMinutes(int(x)))
    print(
        f"SUMMARY: players={len(skatersStats.index)}, games={total_games_played}, points={int(total_points)}, points/game={total_points_per_game:.3f}, score/game={total_score_per_game:.3f}"
    )

    skatersStats = rename_columns(skatersStats)
    print(f'WTF {sortColumn}')
    skatersStats = skatersStats.sort_values(sortColumn, ascending=sortAscending)
    skatersStats = skatersStats.astype({'points': 'int32', 'goals': 'int32', '1stA': 'int32', '2ndA': 'int32'})

    skatersStats = skatersStats[
        [
            'year',
            'name',
            'pos',
            'gp',
            'time/g',
            "points",
            "goals",
            "1stA",
            "2ndA",
            "points/g",
            "points/60",
            'score/60',
            'on_xGoals%',
            'off_xGoals%',
            'onFxGoals',
            'onFgoals',
            'onAxGoals',
            'onAgoals',
            # 'onIce_corsi%',
            # 'offIce_corsi%',
            # 'onIce_fenwick%',
            # 'offIce_fenwick%',
        ]
    ]

    skatersStats = skatersStats.loc[skatersStats['gp'] >= 10]
    skatersStats = skatersStats.head(limit)

    return skatersStats

def rename_columns(df):
    subs = [
        [r'^I_F_', ''],
        [r'[oO]nIce', 'on'],
        [r'[oO]ffIce', 'off'],
        [r'_per_', '/'],
        [r'primary', '1st'],
        [r'secondary', '2nd'],
        [r'games_played', 'gp'],
        [r'Percentage', '%'],
        [r'Assists', 'A'],
        [r'position', 'pos'],
        [r'season', 'year'],
        [r'_F_', 'F'],
        [r'_A_', 'A'],
    ] 

    newColumns = {}
    for name in df.columns.values:
        newName = name
        for sub in subs:
            newName = re.sub(sub[0], sub[1], newName)

        newColumns[name] = newName

    return df.rename(columns=newColumns)

def update_player_lookup():
    if not os.path.exists(MP_ROOT):
        raise ValueError(f"MoneyPuck folder does not exist: {MP_ROOT}")

    req = get(MP_PLAYERS_LOOKUP_URL)
    with open(MP_ROOT + MP_PLAYERS_LOOKUP_FILE, "w", encoding="utf-8") as f:
        f.write(req.content.decode("utf-8"))


def update_skaters(year: int = None):
    if not os.path.isdir(MP_ROOT):
        raise ValueError(f"MoneyPuck folder does not exist: {MP_ROOT}")

    current_year = utils.current_nhl_year()
    if year is None:
        year = current_year

    is_current_year = False
    if year == current_year:
        is_current_year = True

    if not (1900 < year < 2100):
        raise ValueError(f"Invalid year: {year}")

    today = datetime.date.today()

    # If updated today, don't update again
    skaters_file = f"{MP_ROOT}skaters-{year}.csv"
    if os.path.exists(skaters_file):
        if not is_current_year:
            print(f"Skaters {year} file is up to date")
            return
        epoch = os.path.getmtime(skaters_file)
        previous_date = datetime.date.fromtimestamp(epoch)
        if previous_date == today:
            print(f"Skaters {year} file is up to date (last updated {previous_date}, today is {today})")
            return

    # Get data
    skateters_url = f"https://moneypuck.com/moneypuck/playerData/seasonSummary/{year}/regular/skaters.csv"
    try:
        req = get(skateters_url)
        req.raise_for_status()
    except exceptions.HTTPError as e:
        raise SystemExit(f"Cannot download MoneyPuck skaters file: {e.response.status_code}")
    except exceptions.RequestException as e:
        raise SystemExit(f"Cannot download MoneyPuck skaters file: {e}")

    # Backup
    if os.path.exists(skaters_file):
        epoch = os.path.getmtime(skaters_file)
        previous_date = datetime.date.fromtimestamp(epoch)

        backup_file = f"{MP_ROOT}skaters-{year}{previous_date.month:02d}{previous_date.day:02d}.csv"
        if os.path.exists(backup_file):
            raise AssertionError(f"Backup file already exists: {backup_file}")
        shutil.copyfile(skaters_file, backup_file)

    with open(skaters_file, "w", encoding="utf-8") as f:
        f.write(req.content.decode("utf-8"))


def formatToMinutes(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f'{minutes:02}:{seconds:02}'

