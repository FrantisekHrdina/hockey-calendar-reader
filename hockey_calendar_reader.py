#!/usr/bin/env python3
import argparse
import configparser
import logging
import subprocess
import re
from icalendar import Calendar, Event
import requests
import datetime
from dateutil.rrule import *
import pytz
import locale
import os
from dateutil.parser import parse
from pathlib import Path

# email sending
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Event:
    def __init___(self, name, start_time, end_time, created, updated, id):
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.created = created
        self.updated = updated
        self.id = id

    def __str__(self):
        return (
            f"Event:\n"
            f"  Name: {self.name}\n"
            f"  Start Time: {self.start_time}\n"
            f"  End Time: {self.end_time}\n"
            f"  Created: {self.created}\n"
            f"  Updated: {self.updated}\n"
            f"  ID: {self.id}"
        )


def send_email(subject, content):
    sender_email = config['EMAIL-BREVO']['SENDER']
    recipient_emails = recipients  # seznam příjemců, např. ['email1@example.com', 'email2@example.com']
    smtp_server = config['EMAIL-BREVO']['SMTP_SERVER']
    smtp_port = int(config['EMAIL-BREVO']['SMTP_PORT'])
    smtp_username = config['EMAIL-BREVO']['SMTP_LOGIN']
    smtp_password = config['EMAIL-BREVO']['SMTP_PASSWORD']

    # Sestavení emailu
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = ", ".join(recipient_emails)

    # Přidání HTML obsahu
    html_part = MIMEText(content, "html")
    message.attach(html_part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Zapnout TLS
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, recipient_emails, message.as_string())
        print("Email byl odeslán.")
    except Exception as exp:
        logging.error(f"Sending failed: {repr(exp)}")


def print_all_events(all_events):
    for event in all_events:
        print_event(event)


def print_upcoming_events(all_events):
    for event in all_events:
        if event.start_time > datetime.datetime.now(datetime.timezone.utc):
            print_event(event)


def print_specific_upcoming_events(all_events, keyword):
    for event in all_events:
        if keyword in event.name and event.start_time > datetime.datetime.now(datetime.timezone.utc):
            print_event(event)


def print_specific_upcoming_events_to_textfile(all_events, keywords, file_location):
    with open(file_location, 'w', encoding='utf-8') as f:
        for event in all_events:
            if all(keyword.lower() in event.name.lower() for keyword in keywords):
                f.write('{0};{1};{2};{3};{4}\n'
                    .format(
                        event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                        event.end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                        event.name,
                        event.created.strftime('%A %d.%m.%Y %H:%M:%S'),
                        event.updated.strftime('%A %d.%m.%Y %H:%M:%S')
                    )
                )


def print_specific_events_to_textfile(all_events, keywords, file_location):
    with open(file_location, 'w', encoding='utf-8') as f:
        for event in all_events:
            # tmp fix SOLIDA
            if 'bystřec' not in event.name.lower() and 'solida' in event.name.lower():
                compiled = re.compile(re.escape('solida'), re.IGNORECASE)
                res = compiled.sub('SOLIDA Bystřec', event.name)
                event.name = res

            if all(keyword.lower() in event.name.lower() for keyword in keywords):
                f.write('{0};{1};{2};{3};{4};{5}\n'
                    .format(
                        event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                        event.end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                        event.name,
                        event.created.strftime('%A %d.%m.%Y %H:%M:%S'),
                        event.updated.strftime('%A %d.%m.%Y %H:%M:%S'),
                        event.id
                    )
                )


def print_available_events_to_textfile(events, file_location):
    with open(file_location, 'w', encoding='utf-8') as f:
        for i in range(0, len(events) - 1):

            if 'volno' in events[i].name.lower() and events[i].start_time > datetime.datetime.now(datetime.timezone.utc):
                f.write('{0};{1};{2}\n'
                    .format(
                        events[i].start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                        events[i].end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                        events[i].end_time - events[i].start_time
                    )
                )

            time_space = events[i + 1].start_time.replace(tzinfo=pytz.UTC) - events[i].end_time.replace(tzinfo=pytz.UTC)
            if time_space > datetime.timedelta(minutes=15) and events[i].start_time.replace(tzinfo=pytz.UTC) > datetime.datetime.now(datetime.timezone.utc):
                f.write('{0};{1};{2}\n'
                        .format(
                            events[i].end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                            events[i+1].start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                            time_space
                        )
                )


def generate_html_from_text_file(prefix_path, source_file, output_file, headline):
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
            f.write('<tr class="info"><th>Začátek</th><th></th><th>Konec</th><th>Název</th><th>Vytvořeno</th><th>Upraveno</th></tr>')
        for line in loaded_lines:
            splitted = line.split(';')
            f.write(
                '<tr>'
                '<td>{0}</td><td style="text-align: center;">-</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td>'
                '</tr>\n'
                    .format(splitted[0], splitted[1], splitted[2], splitted[3], splitted[4]))

        f.write('</tbody>')
        f.write('</table>\n')
        f.write('</div>\n')
        f.write('</div>\n')
        f.write('</body>\n')
        f.write('</html>\n')


def generate_html_from_text_file_available_events(prefix_path, source_file, output_file, headline):
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
            f.write('<tr class="info"><th>Začátek</th><th></th><th>Konec</th><th>Doba</th><th>Volno</th></tr>')
        for line in loaded_lines:
            splitted = line.split(';')
            f.write(
                '<tr>'
                '<td>{0}</td><td style="text-align: center;">-</td><td>{1}</td><td>{2}</td><td>{3}</td>'
                '</tr>\n'
                    .format(splitted[0], splitted[1], splitted[2], 'volno'))

        f.write('</tbody>')
        f.write('</table>\n')
        f.write('</div>\n')
        f.write('</div>\n')
        f.write('</body>\n')
        f.write('</html>\n')


def print_event(event):
    print(
        '{0} - {1} | {2}'
            .format(
            event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
            event.end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
            event.name
        )
    )


def get_event_by_id(events, id):
    for event in events:
        if event.id == id:
            return event

    return None


def get_ids_of_events_list(events):
    ids = []

    for event in events:
        ids.append(event.id)

    return ids


def parse_czech_date_to_valid_format(czechdate):
    splitted = czechdate.split(' ')
    return parse(splitted[1] + ' ' + splitted[2], dayfirst=True)


def check_news(prefix, filename):
    if not Path(f'{prefix}/{filename}.backup').is_file():
        old_content = ''
        old_lines = []
    else:
        old_content = open('{0}/{1}.backup'.format(prefix, filename), 'r').read()
        with open('{0}/{1}.backup'.format(prefix, filename), 'r') as f:
            old_lines = f.readlines()

    new_content = open('{0}/{1}'.format(prefix, filename), 'r').read()

    if old_content == new_content:
        return

    if not Path(f'{prefix}/{filename}.backup').is_file():
        old_lines = []
    else:
        with open('{0}/{1}.backup'.format(prefix, filename), 'r') as f:
            old_lines = f.readlines()

    old_events = []
    for line in old_lines:
        splitted = line.split(';')
        tmp_event = Event()
        tmp_event.start_time = parse_czech_date_to_valid_format(splitted[0])
        tmp_event.end_time = parse_czech_date_to_valid_format(splitted[1])
        tmp_event.name = splitted[2]
        tmp_event.created = parse_czech_date_to_valid_format(splitted[3])
        tmp_event.updated = parse_czech_date_to_valid_format(splitted[4])
        tmp_event.id = splitted[5]
        old_events.append(tmp_event)

    with open('{0}/{1}'.format(prefix, filename), 'r') as f:
        new_lines = f.readlines()

    new_events = []
    for line in new_lines:
        splitted = line.split(';')
        tmp_event = Event()
        tmp_event.start_time = parse_czech_date_to_valid_format(splitted[0])
        tmp_event.end_time = parse_czech_date_to_valid_format(splitted[1])
        tmp_event.name = splitted[2]
        tmp_event.created = parse_czech_date_to_valid_format(splitted[3])
        tmp_event.updated = parse_czech_date_to_valid_format(splitted[4])
        tmp_event.id = splitted[5]
        new_events.append(tmp_event)

    new_events_ids = get_ids_of_events_list(new_events)
    old_events_ids = get_ids_of_events_list(old_events)
    ids_added = list(set(new_events_ids) - set(old_events_ids))
    ids_removed = list(set(old_events_ids) - set(new_events_ids))

    for id in ids_added:
        event = get_event_by_id(new_events, id)
        message = 'Událost přidana do kalendáře<br>\n' \
                  '<br>\n' \
                  'Název: {0}<br>\n' \
                  'Od: {1}<br>\n' \
                  'Do: {2}<br>\n' \
                  'Přidáno v: {3}<br>\n'.format(
            event.name,
            event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
            event.end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
            event.created.strftime('%A %d.%m.%Y %H:%M:%S')
        )
        send_email('Hockey Calendar Reader - Nová událost', message)

    for id in ids_removed:
        event = get_event_by_id(old_events, id)
        if event.start_time.replace(tzinfo=None) > datetime.datetime.now():
            message = 'Událost začala<br>\n' \
                      '<br>\n' \
                      'Název: {0}<br>\n' \
                      'Od: {1}<br>\n' \
                      'Do: {2}<br>\n'.format(
                event.name,
                event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                event.end_time.strftime('%A %d.%m.%Y %H:%M:%S')
            )
            send_email('Hockey Calendar Reader - Událost začala', message)
        else:
            message = 'Událost zrušena<br>\n' \
                      '<br>\n' \
                      'Název: {0}<br>\n' \
                      'Od: {1}<br>\n' \
                      'Do: {2}<br>\n'.format(
                event.name,
                event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                event.end_time.strftime('%A %d.%m.%Y %H:%M:%S')
            )
            send_email('Hockey Calendar Reader - Událost zrušena', message)

    for new_event in new_events:
        old_event = get_event_by_id(old_events, new_event.id)
        if old_event is not None:
            if old_event.updated != new_event.updated:
                message = 'Událost byla aktualizována' \
                          '<br>\n' \
                          'Nový název: {0}<br>\n' \
                          'Nově od: {1}<br>\n' \
                          'Nově do: {2}<br>\n' \
                          '<br>\n' \
                          'Původní název: {3}<br>\n' \
                          'Původně od: {4}<br>\n' \
                          'Původně do: {5}<br>\n' \
                          '---<br>\n' \
                          '---<br>\n' \
                          'old:<br>\n' \
                          '{6}<br>\n' \
                          'new:<br>\n' \
                          '{7}<br>\n'.format(
                    new_event.name,
                    new_event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                    new_event.end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                    old_event.name,
                    old_event.start_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                    old_event.end_time.strftime('%A %d.%m.%Y %H:%M:%S'),
                    old_event,
                    new_event
                )
                send_email('Hockey Calendar Reader - Událost aktualizována', message)


def backup_file(prefix, filename):
    if Path(f'{prefix}/{filename}').is_file():
        os.system("mv {0}/{1} {0}/{1}.backup".format(prefix, filename))


def get_events_from_calendar(calendar_id):
    url = 'https://www.googleapis.com/calendar/v3/calendars/' + calendar_id + '/events'

    PARAMS = {
        'key': config['CALENDAR']['API_KEY'],
        'singleEvents': 'True',
        'timeMin': datetime.datetime.now().isoformat() + 'Z',
        'orderBy': 'startTime',
        'maxResults': 2500
    }

    events = requests.get(url=url, params=PARAMS).json()['items']

    all_events = []
    for event in events:
        if event['status'] == 'cancelled':
            continue
        if 'dateTime' in event['start']:
            start_time = parse(event['start']['dateTime'])
        else:
            start_time = parse(event['start']['date'])

        if 'dateTime' in event['end']:
            end_time = parse(event['end']['dateTime'])
        else:
            end_time = parse(event['end']['date'])

        if 'summary' not in event.keys():
            continue

        tmp_event = Event()
        tmp_event.id = event['id']
        tmp_event.name = event['summary']
        tmp_event.start_time = start_time
        tmp_event.end_time = end_time
        tmp_event.created = parse(event['created'])
        tmp_event.updated = parse(event['updated'])

        all_events.append(tmp_event)
    
    return all_events


def clean_temp_files():
    subprocess.run(['rm', '-rf', config['GENERAL']['OUTPUT_DIR']])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Hockey-calendar-reader started')
    parser.add_argument('--config', required=True, help='Path to config file')
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(args.config)
    logging.basicConfig(filename=config['GENERAL']['LOG'], format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
    logging.info('Bazoš started')
    recipients = config['GENERAL']['RECIPIENTS'].split(' ')
    locale.setlocale(locale.LC_ALL, "cs_CZ.UTF-8")
    global local_tz
    local_tz = pytz.timezone('Europe/Prague')

    #clean_temp_files()

    Path(config['GENERAL']['OUTPUT_DIR']).mkdir(parents=True, exist_ok=True)

    LA_calendar_id = 'halabmlan@gmail.com'
    CT_calendar_id = 'n7i0r6c4810701q9f4ffvpbjd8@group.calendar.google.com'

    upcoming_events_ceska_trebova = get_events_from_calendar(CT_calendar_id)
    upcoming_events_lanskroun = get_events_from_calendar(LA_calendar_id)

    #prefix_path = '/var/www/my_web/hockey_events/'
    output_dir = config['GENERAL']['OUTPUT_DIR']
    backup_file(output_dir, 'hrdina-la.txt')
    backup_file(output_dir, 'bystrec-la.txt')
    backup_file(output_dir, 'bystrec-ct.txt')
    backup_file(output_dir, 'zapasy-lhl-bystrec.txt')
    backup_file(output_dir, 'zapasy-chl-bystrec.txt')
    backup_file(output_dir, 'bys.txt')

    # Ledy - Hrdina
    print_specific_events_to_textfile(upcoming_events_lanskroun, ['Hrdina'], f'{output_dir}/hrdina-la.txt')
    generate_html_from_text_file(output_dir, 'hrdina-la.txt', 'hrdina-la.html', 'Ledy na jméno Hrdina v Lanškrouně')

    # Volné bruslení
    print_specific_events_to_textfile(upcoming_events_lanskroun, ['volné bruslení'], f'{output_dir}/brusleni-la.txt')
    generate_html_from_text_file(output_dir, 'brusleni-la.txt', 'brusleni-la.html', 'Volné bruslení v Lanškrouně')
    print_specific_events_to_textfile(upcoming_events_ceska_trebova, ['VEŘEJNÉ BRUSLENÍ'],
                                      output_dir + '/' + 'brusleni-ct.txt')
    generate_html_from_text_file(output_dir, 'brusleni-ct.txt', 'brusleni-ct.html', 'Volné bruslení v České Třebové')

    # Ledy - Bystřec
    print_specific_events_to_textfile(upcoming_events_lanskroun, ['Bystřec'], f'{output_dir}/bystrec-la.txt')
    generate_html_from_text_file(output_dir, 'bystrec-la.txt', 'bystrec-la.html', 'Ledy na jméno Bystřec v Lanškrouně')
    print_specific_events_to_textfile(upcoming_events_ceska_trebova, ['Bystřec'], f'{output_dir}/bystrec-ct.txt')
    generate_html_from_text_file(output_dir, 'bystrec-ct.txt', 'bystrec-ct.html',
                                 'Ledy na jméno Bystřec v České Třebové')
    # Ledy - Bys
    print_specific_events_to_textfile(upcoming_events_lanskroun, ['Bys'], f'{output_dir}/bys.txt')
    generate_html_from_text_file(output_dir, 'bys.txt', 'bys.html', 'Ledy na jméno Bystřec v Lanškrouně')


    # Příchozí
    print_specific_events_to_textfile(upcoming_events_lanskroun, ['příchozí'], f'{output_dir}/prichozi-la.txt')
    generate_html_from_text_file(output_dir, 'prichozi-la.txt', 'prichozi-la.html', 'Hokej pro příchozí v Lanškrouně')
    print_specific_events_to_textfile(upcoming_events_ceska_trebova, ['příchozí'], f'{output_dir}/prichozi-ct.txt')
    generate_html_from_text_file(output_dir, 'prichozi-ct.txt', 'prichozi-ct.html',
                                 'Hokej pro příchozí v České Třebové')

    # Naše LHL a CHL zápasy
    print_specific_events_to_textfile(upcoming_events_lanskroun, ['Bystřec', 'LHL'],
                                      f'{output_dir}/zapasy-lhl-bystrec.txt')
    generate_html_from_text_file(output_dir, 'zapasy-lhl-bystrec.txt', 'zapasy-lhl-bystrec.html', 'Zápasy LHL')
    print_specific_events_to_textfile(upcoming_events_ceska_trebova, ['CHL', 'Bystřec'],
                                      f'{output_dir}/zapasy-chl-bystrec.txt')
    generate_html_from_text_file(output_dir, 'zapasy-chl-bystrec.txt', 'zapasy-chl-bystrec.html', 'Zápasy CHL')

    # LHL a CHL zápasy
    print_specific_events_to_textfile(upcoming_events_lanskroun, ['LHL č.'], f'{output_dir}/zapasy-lhl.txt')
    generate_html_from_text_file(output_dir, 'zapasy-lhl.txt', 'zapasy-lhl.html', 'Zápasy LHL')
    print_specific_events_to_textfile(upcoming_events_ceska_trebova, ['CHL'], f'{output_dir}/zapasy-chl.txt')
    generate_html_from_text_file(output_dir, 'zapasy-chl.txt', 'zapasy-chl.html', 'Zápasy CHL')

    # Available events
    print_available_events_to_textfile(upcoming_events_lanskroun, f'{output_dir}/available-la.txt')
    generate_html_from_text_file_available_events(output_dir, 'available-la.txt', 'available-la.html',
                                                  'Volné termíny v Lanškrouně')
    print_available_events_to_textfile(upcoming_events_ceska_trebova, f'{output_dir}/available-ct.txt')
    generate_html_from_text_file_available_events(output_dir, 'available-ct.txt', 'available-ct.html',
                                                  'Volné termíny v České Třebové')

    check_news(output_dir, 'hrdina-la.txt')
    check_news(output_dir, 'bystrec-la.txt')
    check_news(output_dir, 'bystrec-ct.txt')
    check_news(output_dir, 'zapasy-lhl-bystrec.txt')
    check_news(output_dir, 'zapasy-chl-bystrec.txt')

    logging.info('Script ended')

    #clean_temp_files()
