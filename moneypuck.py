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
    mp_parser.add_argument("-y", "--year", type=int, dest="year", default=utils.current_nhl_year(), help="Target year")
    mp_parser.add_argument("-s", "--situation", type=str, dest="situation", default='all', help="On-ice situation: all, 5on5...")
    mp_parser.add_argument("-n", "--nation", type=str, dest="nation", default='fin', help="Nation, e.g. fin, swe, can...")
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
    
    nationStats = getNationStats(args.year, nationality=args.nation, situation=args.situation)
    with pd.option_context('display.precision', 3):
        print(nationStats)


def getPlayer(id: int):
    df = pd.read_csv(MP_ROOT + MP_PLAYERS_LOOKUP_FILE, index_col="playerId")
    return df.loc[id]


def getNationPlayers(nationality:str):
    nationality = nationality.upper()
    df = pd.read_csv(MP_ROOT + "allPlayersLookup.csv", index_col="playerId")
    players = df[df["nationality"] == nationality]
    return players


def getSkatersStats(year: int):
    df = pd.read_csv(MP_ROOT + f"skaters-{year}.csv", index_col="playerId")
    # for x in list(allStats.columns.values):
    #     print(x)
    return df


def getNationStats(year: int, nationality:str='fin', situation:str='all'):
    skatersStats = getSkatersStats(year)

    players = getNationPlayers(nationality)
    playerIds = players.index.to_list()
    nationStats = skatersStats.loc[(skatersStats["situation"] == situation) & skatersStats.index.isin(playerIds)]
    nationStats = nationStats[
        [
            'name',
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
            # "OnIce_F_xGoals",
            # "OnIce_A_xGoals",
        ]
    ]
    nationStats["points_per_game"] = nationStats["I_F_points"] / nationStats["games_played"]
    nationStats["points_per_60"] = nationStats["I_F_points"] / (nationStats["icetime"] / (60 * 60))
    # nationStats["score_per_game"] = nationStats["gameScore"] / nationStats["games_played"]
    nationStats["score_per_60"] = nationStats["gameScore"] / (nationStats["icetime"] / (60 * 60))

    # nationStats = nationStats.sort_values("score_per_game", ascending=False)
    nationStats = nationStats.sort_values("points_per_60", ascending=False)

    total_points = nationStats["I_F_points"].sum()
    total_score = nationStats["gameScore"].sum()
    total_games_played = nationStats["games_played"].sum()
    total_points_per_game = total_points / total_games_played
    total_score_per_game = total_score / total_games_played

    nationStats['icetime'] = nationStats['icetime'] / nationStats["games_played"]
    nationStats['icetime'] = nationStats['icetime'].apply(lambda x: formatToMinutes(int(x)))
    print(
        f"SUMMARY: players={len(nationStats.index)}, games={total_games_played}, points={int(total_points)}, points/game={total_points_per_game:.3f}, score/game={total_score_per_game:.3f}"
    )

    nationStats = rename_columns(nationStats)
    nationStats = nationStats.astype({'points': 'int32', 'goals': 'int32', '1stAssists': 'int32', '2ndAssists': 'int32'})

    nationStats = nationStats[
        [
            'name',
            'games',
            'icetime',
            "points",
            "goals",
            "1stAssists",
            "2ndAssists",
            "points/60",
            'score/60',
            'onIce_xGoals%',
            'offIce_xGoals%',
            # 'onIce_corsi%',
            # 'offIce_corsi%',
            # 'onIce_fenwick%',
            # 'offIce_fenwick%',
        ]
    ]

    nationStats = nationStats.loc[nationStats['games'] >= 10]

    return nationStats


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

def rename_columns(df):
    subs = [
        [r'^I_F_', ''],
        [r'_per_', '/'],
        [r'primary', '1st'],
        [r'secondary', '2nd'],
        [r'games_played', 'games'],
        [r'Percentage', '%']
    ] 

    newColumns = {}
    for name in df.columns.values:
        newName = name
        for sub in subs:
            newName = re.sub(sub[0], sub[1], newName)

        newColumns[name] = newName

    return df.rename(columns=newColumns)
