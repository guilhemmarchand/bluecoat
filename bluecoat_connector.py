#!/usr/bin/python
# -*- coding: utf-8 -*-

# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json
import os
import requests
from urllib.parse import urlparse  # Correct import for Python 3

from django.http import HttpResponse

# Phantom App imports if available, example imports shown
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

from bluecoat_consts import *  # Ensure this file is Python 3 compatible

def handle_request(request, path_parts):
    list_data = _load_data()
    blacklist = list_data.get('blacklist', [])
    whitelist = list_data.get('whitelist', [])
    full_list = '''define category phantom_blacklist
    {}
    end
    define category phantom_whitelist
    {}
    end'''
    return HttpResponse(full_list.format('\n'.join(blacklist), '\n'.join(whitelist)))

def _load_data(list_mgr_connector=None):
    dir_path = os.path.split(__file__)[0]
    list_data_file = f'{dir_path}/data/list_data.json'
    list_data = {'blacklist': [], 'whitelist': []}
    try:
        if os.path.isfile(list_data_file):
            with open(list_data_file, 'r') as f:
                list_json = f.read()
                list_data = json.loads(list_json)
    except Exception as e:
        if list_mgr_connector:
            list_mgr_connector.debug_print(f'In _load_data: Exception: {str(e)}')
    if list_mgr_connector:
        list_mgr_connector.debug_print('Loaded state: ', list_data)
    return list_data

def _save_data(list_data, list_mgr_connector):
    dir_path = os.path.split(__file__)[0]
    list_data_file = f'{dir_path}/data/list_data.json'
    if list_mgr_connector:
        list_mgr_connector.debug_print('Saving state: ', list_data)
    try:
        with open(list_data_file, 'w') as f:
            f.write(json.dumps(list_data))
            f.flush()
    except Exception as e:
        return phantom.APP_ERROR
    return phantom.APP_SUCCESS

class BlueCoatConnector(BaseConnector):
    ACTION_ID_BLOCK_URL = 'block_url'
    ACTION_ID_UNBLOCK_URL = 'unblock_url'
    ACTION_ID_ALLOW_URL = 'allow_url'
    ACTION_ID_DISALLOW_URL = 'disallow_url'
    ACTION_ID_URL_REPUTATION = 'url_reputation'

    def __init__(self):
        super(BlueCoatConnector, self).__init__()
        self._list_data = {}

    def initialize(self):
        self._list_data = _load_data(self)
        return phantom.APP_SUCCESS

    def finalize(self):
        _save_data(self._list_data, self)
        return phantom.APP_SUCCESS

    def _test_connectivity(self, param):
        config = self.get_config()
        self.save_progress('Querying proxy server to check connectivity')
        try:
            r = requests.get(TEST_URL.format(config['proxy_host'],
                                             config['proxy_mgmt_port'],
                                             'http://www.google.com'),
                             auth=(config['username'], config['password']),
                             verify=config[phantom.APP_JSON_VERIFY])
            r.raise_for_status()
        except requests.HTTPError as e:
            self.set_status(phantom.APP_ERROR, ERR_SERVER_CONNECTION, e)
            self.append_to_message(ERR_CONNECTIVITY_TEST)
            return self.get_status()
        return self.set_status_save_progress(phantom.APP_SUCCESS, SUCC_CONNECTIVITY_TEST)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS
        action_id = self.get_action_identifier()
        self.debug_print("action_id", action_id)
        if action_id == self.ACTION_ID_BLOCK_URL:
            ret_val = self._handle_block_url(param)
        elif action_id == self.ACTION_ID_UNBLOCK_URL:
            ret_val = self._handle_unblock_url(param)
        elif action_id == self.ACTION_ID_ALLOW_URL:
            ret_val = self._handle_allow_url(param)
        elif action_id == self.ACTION_ID_DISALLOW_URL:
            ret_val = self._handle_disallow_url(param)
        elif action_id == self.ACTION_ID_URL_REPUTATION:
            ret_val = self._handle_url_reputation(param)
        elif action_id == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)
        return ret_val

    def _handle_block_url(self, param):
        url = urlparse(param[BLUECOAT_JSON_URL]).netloc
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)
        if url in self._list_data['blacklist']:
            action_result.set_status(phantom.APP_ERROR, ERR_BLOCK_URL)
            return action_result.get_status()
        self._list_data['blacklist'].append(url)
        action_result.add_data(self._list_data)
        return action_result.set_status(phantom.APP_SUCCESS, SUCC_BLOCK_URL)

    def _handle_unblock_url(self, param):
        url = urlparse(param[BLUECOAT_JSON_URL]).netloc
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)
        try:
            self._list_data['blacklist'].remove(url)
            action_result.add_data(self._list_data)
        except ValueError:
            action_result.set_status(phantom.APP_ERROR, ERR_UNBLOCK_URL)
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS, SUCC_UNBLOCK_URL)

    def _handle_allow_url(self, param):
        url = urlparse(param[BLUECOAT_JSON_URL]).netloc
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)
        if url in self._list_data['whitelist']:
            action_result.set_status(phantom.APP_ERROR, ERR_ALLOW_URL)
            return action_result.get_status()
        self._list_data['whitelist'].append(url)
        action_result.add_data(self._list_data)
        return action_result.set_status(phantom.APP_SUCCESS, SUCC_ALLOW_URL)

    def _handle_disallow_url(self, param):
        url = urlparse(param[BLUECOAT_JSON_URL]).netloc
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)
        try:
            self._list_data['whitelist'].remove(url)
            action_result.add_data(self._list_data)
        except ValueError:
            action_result.set_status(phantom.APP_ERROR, ERR_DISALLOW_URL)
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS, SUCC_DISALLOW_URL)

    def _handle_url_reputation(self, param):
        # Update this function if needed to use urlparse or other details relevant to URL handling

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('No test json specified as input')
        exit(0)
    with open(sys.argv[1]) as my_f:
        in_json = my_f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = BlueCoatConnector()
        connector.print_progress_message = True
        my_ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(my_ret_val), indent=4))
    exit(0)
