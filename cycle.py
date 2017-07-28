# -*- coding: utf-8 -*-
# get the number of available bicycles in a docomo cycle park.
# this software is unofficial.

import re
import os
import csv
import getpass
import codecs
import time
import requests
import xml.etree.ElementTree

class CycleWeb(object):
    def __init__(self):
        pass

    def login(self, user_id, password):
        # login page:
        #r = requests.get('https://tcc.docomo-cycle.jp/cycle/TYO/cs_web_main.php')
        #print(r.text)
        data = {
            'EventNo': '21401',
            'MemberID': user_id,
            'Password': password,
        }
        r = requests.post('https://tcc.docomo-cycle.jp/cycle/TYO/cs_web_main.php', data=data)
        mo = re.search('"SessionID" value="(.*?)">', r.text, re.M)
        if not mo:
            print('failed to login as {}'.format(self.UserID))
            return False
        self.UserID = user_id
        self.SessionID = mo.groups()[0]
        print('logged in as {}. SessionID = {}'.format(self.UserID, self.SessionID))
        return True
    
    area_ids = {
            u'千代田': 1,
            u'中央': 2,
            u'港': 3,
            u'江東': 4,
            u'新宿': 5,
            u'文京': 6,
        }

    def find_parks(self, area_id):
        data = {
            'EventNo': '21615',
            'UserID': 'TYO',
            'MemberID': self.UserID,
            'SessionID': self.SessionID,
            'GetInfoNum': 20,
            'GetInfoTopNum': 1,
            'MapType': 1,
            'AreaID': area_id,
        }
        park_list = [] # park_id, name, num
        park_pattern = r'<input type="hidden" name="ParkingID" value="(.*?)">\s*' + \
                       r'<input type="submit" value="(.*?)\s*" style="min-width:150px; text-align:left">.*?（(\d+)台）'
        NextCycleTop = 1
        while True:
            r = requests.post('https://tcc.docomo-cycle.jp/cycle/TYO/cs_web_main.php', data=data)
            #print(r.text)
            for park_id, name, num in re.findall(park_pattern, r.text, re.M | re.S):
                print(park_id, name, num)
                park_list.append((park_id, name, num))
            if not re.search(r'次の20件→', r.text, re.M):
                break
            try:
                # only for the first query.
                del data['GetInfoTopNum']
                del data['GetInfoNum']
            except KeyError:
                pass
            # for "next" query.
            NextCycleTop += 20
            data['EventNo'] = '22302'
            data['NextCycleTop'] = NextCycleTop
            print('wait..')
            time.sleep(3)
        return park_list


def create_park_list_csv(out_path):
    u'''scrape the park list pages and create a CSV containing region, id, name of all parks'''
    api = CycleWeb()
    user_id  = input('User> ')
    password = getpass.getpass('Pass> ')
    if not api.login(user_id, password):
        raise RuntimeError('failed to log in.')

    with codecs.open(out_path, 'wb', encoding='utf-8-sig') as fo:
        writer = csv.writer(fo)
        writer.writerow(['region', 'park_id', 'name'])
        for region, area_id in api.area_ids.items():
            park_list = api.find_parks(area_id)
            for park_id, name, n_available in park_list:
                writer.writerow(map(str, [region, park_id, name]))

def get_bikes(park_id):
    api_url = 'https://tcc.docomo-cycle.jp/cgi-bin/csapi/csapiVD'
    query_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <csreq>
        <msgtype>3</msgtype>
        <aplcode>43C27EC677B036A343A6F7B08CEC40BB</aplcode>
        <park_id>{:08d}</park_id>
        <get_num>100</get_num>
        <get_start_no>1</get_start_no>
    </csreq>'''.format(park_id)

    headers = {
        'Content-Type': 'application/xml',
    }
    req = requests.post(api_url, data=query_xml, headers=headers)
    #print(req.text)

    root = xml.etree.ElementTree.fromstring(req.text)
    total_num = int(root.find('.//total_num').text)
    return total_num


if __name__ == '__main__':
    csv_file = 'docomo_cycle_parks.csv'
    if not os.path.isfile(csv_file):
        # create CSV mode
        create_park_list_csv(csv_file)
    else:
        # find bicycles demo
        with codecs.open(csv_file, 'rb', encoding='utf-8-sig') as fi:
            reader = csv.reader(fi)
            next(reader) # header
            for region, park_id, name in reader:
                n_bikes = get_bikes(int(park_id))
                print(region, park_id, name, n_bikes)
                time.sleep(0.5)