import datetime

def current_nhl_year():
    today = datetime.date.today()
    year = today.year
    if today.month < 9:
        year = year - 1
    return year
