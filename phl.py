import nhlapi
import pprint
import sys
import moneypuck as mp
import datetime
import argparse

pp = pprint.PrettyPrinter(indent=4, width=130)

def current_nhl_year():
    today = datetime.date.today()
    year = today.year
    if today.month < 9:
        year = year - 1
    return year

# NHL API
def nhl_command(alpha):
    print('nhl', alpha)



# Player
def player_command(args):
    if args.id.isdecimal():
        pid = int(args.id)
    else:
        pid = 8470000

    if args.api=='nhl':
        player = nhlapi.getPlayer(pid)
    else:
        player = mp.getPlayer(pid)

    pp.pprint(player)


# Finns
def finns_command(args):
    year = args.year
    if year == 0:
        year = current_nhl_year()
    # finns = mp.getFinns()
    finns = mp.finnStats(year)
    print(finns)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')

    player_parser = subparsers.add_parser('player')
    player_parser.add_argument('id')
    player_parser.add_argument(
        '-a', '--api', dest='api', default='nhl', help='Used API')
    player_parser.set_defaults(func=player_command)

    player_parser = subparsers.add_parser('finns')
    player_parser.set_defaults(func=finns_command)
    player_parser.add_argument(
        '-y', '--year', dest='year', default=0, type=int, help='Year')

    nhl_parser = subparsers.add_parser('nhl')
    nhl_parser.add_argument(
        '-a', '--alpha', dest='nhl', help='Alpha description')
    nhl_parser.set_defaults(func=nhl_command)

    mp.add_parser(subparsers)


    args = parser.parse_args()
    args.func(args)




# t = nhlapi.getTeam('predators')
# print(t)

# p = nhlapi.getPlayers(sys.argv[1])
# p = list(map(lambda x: x['person'], p))
# pp.pprint(p)

# print("ALL")
# p2 = nhlapi.getPlayers2(sys.argv[1])
# p2 = list(map(lambda x: x['person'], p2))
# pp.pprint(p2)

# p = nhlapi.getPlayer(8480947)
# p = nhlapi.getPlayer(sys.argv[1])
# pp.pprint(p)

# nhlapi.getFins()

# if len(sys.argv) > 1:
#     print(nhlapi.getPlayer(sys.argv[1]))
#     exit()

# mp.getPlayer(8480000)
# mp.finStats(2021)