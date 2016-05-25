import csv
import os
import sys
from datetime import datetime
from os.path import exists, join
from configparser import ConfigParser
# import dateparser
import time
import requests
from bs4 import BeautifulSoup, ResultSet, Tag

from collections import namedtuple

FORMATS = {
    'percent': lambda value: float(value.replace('%', '')),
    'temperature': lambda value: float(value.replace('°C', '')),
    'string': str,
    'number': float
}


def parse_page(body: str)->dict:
    def parse_date(s: str):
        return datetime.strptime(s.strip(), "%d.%m.%Y %H:%M:%S")

    soup = BeautifulSoup(body, "html.parser")

    items = {
        item.find(class_='sensorname').string: item.find(class_='sensorvalue').string
        for item in soup(class_='sensortable')
    }

    time_str = soup.find(class_='datetime').contents[0]

    return {
        'time': parse_date(time_str),
        'items': items
    }


def read_table(file_name: str, column_names: list)->list:
    if not exists(file_name):
        return []
    else:
        with open(file_name, encoding='utf-8') as f:
            reader = csv.DictReader(f)

            if reader.fieldnames != ['time'] + column_names:
                raise ValueError("Columns do not match with old file")
            return list(reader)


def read_column_defs(c: ConfigParser):
    return [{
            'name': s.replace('column:', ''),
            'format': FORMATS[c[s]['format']]
        }
        for s in c.sections()
        if s.startswith('column:')
    ]


def page_to_row(page: dict, column_defs: list)->list:
    items = page['items']
    row = {}

    for col in column_defs:
        col_name = col['name']
        formatter = col['format']
        row[col_name] = formatter(items[col_name])

    row['time'] = page['time']
    return row


def main(c: ConfigParser):
    log_dir = c['main']['log directory']
    page_url = c['main']['page url']

    log_file = join(log_dir,
                    datetime.now().strftime(
                        'log-%Y-%m-%d.csv'
                    ))
    r = requests.get(page_url)
    r.encoding = 'utf-8'
    page = parse_page(r.text)

    # Skipping [main] section
    column_defs = read_column_defs(c)
    column_names = [
        column_def['name']
        for column_def in column_defs
    ]

    table = read_table(log_file, column_names)
    table.append(page_to_row(page, column_defs))

    os.makedirs(log_dir, exist_ok=True)
    with open(log_file, 'w', encoding='utf-8', newline='\n') as f:
        writer = csv.DictWriter(f, fieldnames=['time']+column_names)
        writer.writeheader()
        writer.writerows(table)


if __name__ == '__main__':
    c = ConfigParser()
    with open('./config.ini', encoding='utf-8') as f:
        c.read_string(f.read())

    update_time = int(c['main']['update interval'])
    while True:
        try:
            main(c)
            time.sleep(update_time)
        except Exception as e:
            print(e)
            time.sleep(10)


