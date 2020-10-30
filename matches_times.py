#!/usr/bin/env python3

from icalendar import Calendar, Event
import requests
import datetime
from dateutil.rrule import *
import pytz
import locale
import os
import smtplib
from dateutil.parser import parse
import re


class Event:
    def __init___(self, name, start_time, end_time, created, updated, id):
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.created = created
        self.updated = updated
        self.id = id


class Team_Stat:
    def __init__(self, name):
        self.name = name

        self.count = 0


def get_events_from_calendar(calendar_id):
    api_key = ''
    url = 'https://www.googleapis.com/calendar/v3/calendars/' + calendar_id + '/events'

    PARAMS = {
        'key': api_key,
        'singleEvents': 'True',
        'timeMin': datetime.datetime(2019, 9, 1).isoformat() + 'Z',
        'orderBy': 'startTime',
        'maxResults': 2500
    }

    events = requests.get(url=url, params=PARAMS).json()['items']

    all_events = []
    for event in events:
        if 'summary' not in event.keys():
            continue
        if event['status'] == 'cancelled':
            continue
        if 'LHL' not in event['summary']:
            continue
        if 'dateTime' in event['start']:
            start_time = parse(event['start']['dateTime'])
        else:
            start_time = parse(event['start']['date'])

        if 'dateTime' in event['end']:
            end_time = parse(event['end']['dateTime'])
        else:
            end_time = parse(event['end']['date'])

        tmp_event = Event()
        tmp_event.id = event['id']
        tmp_event.name = event['summary']
        tmp_event.start_time = start_time
        tmp_event.end_time = end_time
        tmp_event.created = parse(event['created'])
        tmp_event.updated = parse(event['updated'])

        all_events.append(tmp_event)

    return all_events


def get_time_interval(given_datetime):
    #        hour_1 = {'6-10': 0, '10-12': 0, '12-20': 0, '20-22': 0, '22-23': 0}

    if given_datetime.hour < 10:
        return '6-10'
    elif given_datetime.hour >=10 and given_datetime.hour < 12:
        return '10-12'
    elif given_datetime.hour >= 12 and given_datetime.hour < 20:
        return '12-20'
    elif given_datetime.hour >= 20 and given_datetime.hour < 22:
        return '20-22'
    else:
        return '22-23'


def print_to_text_file(teams, file_location):
    with open(file_location, 'w', encoding='utf-8') as f:
        for team in teams.keys():
            f.write('{0};{1};'.format(teams[team]['name'], teams[team]['matches_count']))
            for day_interval in teams[team]['days'].keys():
                f.write('{0};'.format(teams[team]['days'][day_interval]))

            for hour_interval in teams[team]['hours'].keys():
                f.write('{0};'.format(teams[team]['hours'][hour_interval]))
            f.write('{0};'.format(teams[team]['late_minutes']))
            f.write('\n')


def generate_html_days(prefix_path, source_file, output_file, headline):
    loaded_lines = open('{0}/{1}'.format(prefix_path, source_file), 'r', encoding='utf-8').readlines()

    with open('{0}/{1}'.format(prefix_path, output_file), 'w', encoding='utf-8') as f:
        f.write('<html>\n')
        f.write('<head>\n')
        f.write('<meta charset="UTF-8">\n')
        f.write('<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">')
        f.write('<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css" integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp" crossorigin="anonymous">')
        f.write('<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>')
        f.write('<title>{0}</title>\n'.format(headline))
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('<div style="text-align: center; align-self: center; margin: auto; align-content: center;">\n')
        f.write('<h2>{0}</h2>\n'.format(headline))
        f.write('<h4>Aktualizováno v {0} </h4>\n'.format(datetime.datetime.now().strftime('%A %d.%m.%Y %H:%M:%S')))
        f.write('<div class="panel panel-default" style="width: 90%; align-self: center;margin: auto;">\n')
        f.write('<table class="table table-hover table-responsive table-bordered" style="width: 100%; margin: auto">\n')
        f.write('<tbody>\n')
        if len(loaded_lines) == 0:
            f.write('<tr><td colspan="3" style="text-align: center">Žádná požadovaná událost nebyla v kalendáři nalezena</td></tr>\n')
        else:
            f.write('<tr class="info"><th>Tým</th><th>Zápasy</th><th>Pondělí</th><th>Úterý</th><th>Středa</th><th>Čtvrtek</th><th>Pátek</th><th>Sobota</th><th>Neděle</th></tr>')
        for line in loaded_lines:
            splitted = line.split(';')
            f.write(
                '<tr>'
                '<td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td><td>{6}</td><td>{7}</td><td>{8}</td>'
                '</tr>\n'
                    .format(splitted[0], splitted[1], splitted[2], splitted[3], splitted[4], splitted[5], splitted[6], splitted[7], splitted[8]))

        f.write('</tbody>')
        f.write('</table>\n')
        f.write('</div>\n')
        f.write('</div>\n')
        f.write('</body>\n')
        f.write('</html>\n')


def generate_html_hours(prefix_path, source_file, output_file, headline):
    loaded_lines = open('{0}/{1}'.format(prefix_path, source_file), 'r', encoding='utf-8').readlines()

    with open('{0}/{1}'.format(prefix_path, output_file), 'w', encoding='utf-8') as f:
        f.write('<html>\n')
        f.write('<head>\n')
        f.write('<meta charset="UTF-8">\n')
        f.write('<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">')
        f.write('<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css" integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp" crossorigin="anonymous">')
        f.write('<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>')
        f.write('<title>{0}</title>\n'.format(headline))
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('<div style="text-align: center; align-self: center; margin: auto; align-content: center;">\n')
        f.write('<h2>{0}</h2>\n'.format(headline))
        f.write('<h4>Aktualizováno v {0} </h4>\n'.format(datetime.datetime.now().strftime('%A %d.%m.%Y %H:%M:%S')))
        f.write('<div class="panel panel-default" style="width: 90%; align-self: center;margin: auto;">\n')
        f.write('<table class="table table-hover table-responsive table-bordered" style="width: 100%; margin: auto">\n')
        f.write('<tbody>\n')
        if len(loaded_lines) == 0:
            f.write('<tr><td colspan="3" style="text-align: center">Žádná požadovaná událost nebyla v kalendáři nalezena</td></tr>\n')
        else:
            f.write('<tr class="info"><th>Tým</th><th>Zápasy</th><th>6-10h</th><th>10-12h</th><th>12-20h</th><th>20-22h</th><th>22h-</th></tr>')
        for line in loaded_lines:
            splitted = line.split(';')
            f.write(
                '<tr>'
                '<td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td><td>{6}</td>'
                '</tr>\n'
                    .format(splitted[0], splitted[1], splitted[9], splitted[10], splitted[11], splitted[12], splitted[13]))

        f.write('</tbody>')
        f.write('</table>\n')
        f.write('</div>\n')
        f.write('</div>\n')
        f.write('</body>\n')
        f.write('</html>\n')


def generate_html_late_minutes(prefix_path, source_file, output_file, headline):
    loaded_lines = open('{0}/{1}'.format(prefix_path, source_file), 'r', encoding='utf-8').readlines()

    teams = []
    for line in loaded_lines:
        splitted = line.split(';')
        teams.append((splitted[0], int(splitted[14])))

    teams.sort(key=lambda tup: tup[1], reverse=True)

    with open('{0}/{1}'.format(prefix_path, output_file), 'w', encoding='utf-8') as f:
        f.write('<html>\n')
        f.write('<head>\n')
        f.write('<meta charset="UTF-8">\n')
        f.write(
            '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">')
        f.write(
            '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css" integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp" crossorigin="anonymous">')
        f.write(
            '<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>')
        f.write('<title>{0}</title>\n'.format(headline))
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('<div style="text-align: center; align-self: center; margin: auto; align-content: center;">\n')
        f.write('<h2>{0}</h2>\n'.format(headline))
        f.write('<h4>Aktualizováno v {0} </h4>\n'.format(datetime.datetime.now().strftime('%A %d.%m.%Y %H:%M:%S')))
        f.write('<div class="panel panel-default" style="width: 50%; align-self: center;margin: auto;">\n')
        f.write('<table class="table table-hover table-responsive table-bordered" style="width: 100%; margin: auto">\n')
        f.write('<tbody>\n')
        if len(loaded_lines) == 0:
            f.write(
                '<tr><td colspan="3" style="text-align: center">Žádná požadovaná událost nebyla v kalendáři nalezena</td></tr>\n')
        else:
            f.write(
                '<tr class="info"><th>Tým</th><th>Počet minut odehraných v pozdních hodinách</th></tr>')
        for team in teams:
            f.write(
                '<tr><td>{0}</td><td>{1}</td>''</tr>\n'.format(team[0], team[1]))

        f.write('</tbody>')
        f.write('</table>\n')
        f.write('</div>\n')
        f.write('</div>\n')
        f.write('</body>\n')
        f.write('</html>\n')


def fix_inconsistent_team_names(given_name):
    if given_name == 'Trnávka':
        return 'Udánky'
    if given_name == 'Snakes':
        return 'Snakes D.Dobrouč'
    if given_name == 'H.Třešňovec':
        return 'Horní Třešňovec'
    if given_name == 'Horní Čerrmná':
        return 'Horní Čermná'
    if given_name == 'Slámožrouti':
        return 'Slámožrouti Kunvald'
    if given_name == 'Klášterec':
        return 'Sokol Klášterec'
    if given_name == 'Sloni':
        return 'Sloni D. Morava'
    if given_name == 'Wild Band':
        return 'Wild Band Zábřeh'
    if given_name.startswith('LDM'):
        return 'LDM'

    return given_name


def late_minutes(start_time, end_time):
    holidays = [
        datetime.date(2019, 9, 28),
        datetime.date(2019, 10, 28),
        datetime.date(2019, 11, 17),
        datetime.date(2019, 12, 24),
        datetime.date(2019, 12, 25),
        datetime.date(2019, 12, 26),
        datetime.date(2020, 1, 1)
    ]

    # weekday 0-po, ... 6-ne

    second_day = end_time + datetime.timedelta(days=1)
    boundary_before_freeday = 23
    boundary_before_workday = 22

    # Druhy den je sobota nebo nedele, nebo svatek
    holiday_check = datetime.date(second_day.year, second_day.month, second_day.day) in holidays
    if second_day.weekday() in [5,6] or holiday_check:
        boundary = datetime.datetime(end_time.year, end_time.month, end_time.day, boundary_before_freeday, 0, 0)
    else:
        boundary = datetime.datetime(end_time.year, end_time.month, end_time.day, boundary_before_workday, 0, 0)

    if start_time.replace(tzinfo=None) > boundary:
        boundary = datetime.datetime(end_time.year, end_time.month, end_time.day, start_time.hour, start_time.minute, start_time.second)

    if boundary >= end_time.replace(tzinfo=None):
        return 0
    else:
        return int((end_time.replace(tzinfo=None) - boundary).seconds / 60)


def main():
    locale.setlocale(locale.LC_ALL, "cs_CZ.UTF-8")
    global local_tz
    local_tz = pytz.timezone('Europe/Prague')

    LA_calendar_id = 'halabmlan@gmail.com'

    events = get_events_from_calendar(LA_calendar_id)

    regex = re.compile(r'.*\d+(.*)\\(.*)\d\.liga')

    teams = {}

    for event in events:
        matched = regex.match(event.name)
        if matched is None:
            continue

        team1 = fix_inconsistent_team_names(matched.group(1).replace('!', '').strip())
        team2 = fix_inconsistent_team_names(matched.group(2).strip())

        day1 = {'0' : 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}
        day2 = {'0' : 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}

        hour_1 = {'6-10': 0, '10-12': 0, '12-20': 0, '20-22': 0, '22-23': 0}
        hour_2 = {'6-10': 0, '10-12': 0, '12-20': 0, '20-22': 0, '22-23': 0}

        tmp_team1 = {'name': team1, 'matches_count': 1, 'days': day1, 'hours': hour_1, 'late_minutes': 0}
        tmp_team2 = {'name': team2, 'matches_count': 1, 'days': day2, 'hours': hour_2, 'late_minutes': 0}

        if team1 not in teams.keys():
            teams[team1] = tmp_team1
        else:
            teams[team1]['matches_count'] += 1

        teams[team1]['days'][str(event.start_time.weekday())] += 1
        teams[team1]['hours'][get_time_interval(event.start_time)] += 1

        teams[team1]['late_minutes'] += late_minutes(event.start_time, event.end_time)

        if team2 not in teams.keys():
            teams[team2] = tmp_team2
        else:
            teams[team2]['matches_count'] += 1

        teams[team2]['days'][str(event.start_time.weekday())] += 1
        teams[team2]['hours'][get_time_interval(event.start_time)] += 1
        teams[team2]['late_minutes'] += late_minutes(event.start_time, event.end_time)

    prefix_path = '/var/www/my_web/hockey_events/'

    print_to_text_file(teams, prefix_path + 'teams_dates.txt')
    generate_html_days(prefix_path, 'teams_dates.txt', 'teams_dates.html', 'Zápasy v jednotlivé dny')
    generate_html_hours(prefix_path, 'teams_dates.txt', 'teams_hours.html', 'Zápasy v jednotlivé hodiny')
    generate_html_late_minutes(prefix_path, 'teams_dates.txt', 'teams_late_minutes.html', 'Čas odehraný v pozdních hodinách (po 22h před pracovním dnem, po 23h před volnem)')


if __name__ == '__main__':
    main()
