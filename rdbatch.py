import csv
import requests
from time import sleep

###### PROGRAM CONSTANTS ######

CSV_FILE = 'carts.csv'

RD_HOST = '127.0.0.1'
RD_USER = 'user'
RD_PSWD = ''

UPDATE_CARTS = True
UPDATE_CUTS = True
UPDATE_SCHED_CODES = False

LOOP_WAIT_MS = 10

###############################


def logo() -> None:
    print('''
 _______   _______   _______              __                __       
|       \ |       \ |       \            |  \              |  \      
| $$$$$$$\| $$$$$$$\| $$$$$$$\  ______  _| $$_     _______ | $$____  
| $$__| $$| $$  | $$| $$__/ $$ |      \|   $$ \   /       \| $$    \ 
| $$    $$| $$  | $$| $$    $$  \$$$$$$\\$$$$$$  |  $$$$$$$| $$$$$$$\\
| $$$$$$$\| $$  | $$| $$$$$$$\ /      $$ | $$ __ | $$      | $$  | $$
| $$  | $$| $$__/ $$| $$__/ $$|  $$$$$$$ | $$|  \| $$_____ | $$  | $$
| $$  | $$| $$    $$| $$    $$ \$$    $$  \$$  $$ \$$     \| $$  | $$
 \$$   \$$ \$$$$$$$  \$$$$$$$   \$$$$$$$   \$$$$   \$$$$$$$ \$$   \$$

  Cart database bulk importer for Rivendell Radio Automation | v1.1
    ''')


class CWebAPI():
    def __init__(self):
        self.host = RD_HOST
        self.username = RD_USER
        self.password = RD_PSWD
        self.endpoint = f'http://{self.host}/rd-bin/rdxport.cgi'
        self.error_count = 0
        self.error_carts = []

    def _post(self, payload: object) -> None:
        r = requests.post(self.endpoint, data=payload)

        if not r.ok:
            self.error_carts.append(payload['CART_NUMBER'])
            self.error_count += 1

    def update_cart(self, cart: object) -> None:
        payload = {
            'COMMAND': 14,
            'LOGIN_NAME': self.username,
            'PASSWORD': self.password,
            'TICKET': '',
            'CART_NUMBER': cart['cart_number'],
            'INCLUDE_CUTS': cart['cut_number'],
            # 'ASYNCHRONOUS': cart['asynchronous'],
            # 'ENFORCE_LENGTH': cart['enforce_length'],
            'GROUP_NAME': cart['group_name'],
            'TITLE': cart['title'],
            'ARTIST': cart['artist'],
            'YEAR': cart['year'],
            'SONG_ID': cart['song_id'],
            'ALBUM': cart['album'],
            'LABEL': cart['label'],
            'CLIENT': cart['client'],
            'AGENCY': cart['agency'],
            'PUBLISHER': cart['publisher'],
            'COMPOSER': cart['composer'],
            'CONDUCTOR': cart['conductor'],
            'USER_DEFINED': cart['user_defined'],
            'NOTES': cart['description']
        }
        self._post(payload)

    def update_cut(self, cart: object) -> None:
        payload = {
            'COMMAND': 15,
            'LOGIN_NAME': self.username,
            'PASSWORD': self.password,
            'TICKET': '',
            'CART_NUMBER': cart['cart_number'],
            'CUT_NUMBER': cart['cut_number'],
            # 'EVERGREEN': cart['evergreen'],
            # 'DESCRIPTION': cart['description'],
            'OUTCUE': cart['outcue'],
            'ISRC': cart['isrc'],
            'ISCI': cart['isci'],
            # Currently we don't bother supporting timers
        }
        self._post(payload)

    def assign_sched_codes(self, cart: object) -> None:
        sched_codes = cart['sched_codes'].split('|')

        for code in sched_codes:
            payload = {
                'COMMAND': 25,
                'LOGIN_NAME': self.username,
                'PASSWORD': self.password,
                'TICKET': '',
                'CART_NUMBER': cart['cart_number'],
                'CODE': code
            }
            self._post(payload)


def import_csv_data(csv_file: str) -> list:
    lines = []

    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            lines.append(row)

    lines.pop(0)  # remove headers

    return parse_cart_data(lines)  # morph to internal data structure


def parse_cart_data(lines: list) -> list:
    carts = []
    for line in lines:
        carts.append({
            'cart_number': line[0],
            'cut_number': line[1],
            'type': line[2],
            'group_name': line[3],
            'title': line[4],
            'artist': line[5],
            'album': line[6],
            'year': line[7],
            'isrc': line[8],
            'isci': line[9],
            'label': line[10],
            'client': line[11],
            'agency': line[12],
            'publisher': line[13],
            'composer': line[14],
            'conductor': line[15],
            'song_id': line[16],
            'user_defined': line[17],
            'description': line[18],
            'outcue': line[19],
            'sched_codes': line[32],
        })
    return carts

# Print iterations progress


def progress(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)

    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)

    if iteration >= total:
        print()


if __name__ == '__main__':
    api = CWebAPI()

    logo()

    print(f'[INF] Importing cart data from {CSV_FILE}...')

    carts = import_csv_data(CSV_FILE)
    total_carts = len(carts)

    print(f'[INF] Starting batch update of {total_carts} carts...')

    for i, cart in enumerate(carts):
        if UPDATE_CARTS:
            api.update_cart(cart)
        if UPDATE_CUTS:
            api.update_cut(cart)
        if UPDATE_SCHED_CODES:
            api.assign_sched_codes(cart)
        progress(i+1, total_carts,
                 f'[INF] {i+1} of {total_carts}', 'Complete', 1, 30)
        
        sleep(LOOP_WAIT_MS / 1000)

    if api.error_count == 0:
        print('[INF] All carts succesfully updated. Goodbye!')
    else:
        f'[ERR] {api.error_count} errors encountered during batch update. The following cuts were affected: {api.error_carts}'
