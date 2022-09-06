# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #

__author__ = 'jradhakrishna'

import json
import time
import requests
import urllib3
import getpass
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import re

class Utils:
    def __init__(self, args):
        self.hostname = args[0]
        self.username = args[1]
        self.password = args[2]
        self.header = {'Content-Type': 'application/json'}
        self.token_url = 'https://'+ self.hostname +'/v1/tokens'
        self.get_token()
    
    def get_token(self):
        payload = {"username": self.username,"password": self.password}
        response = self.post_request(payload=payload,url=self.token_url)
        token = response['accessToken']
        self.header['Authorization'] = 'Bearer ' + token
    
    def get_request(self,url):
        self.get_token()
        time.sleep(5)
        response = requests.get(url, headers=self.header,verify=False)
        if(response.status_code == 200 or response.status_code == 202):
            data = json.loads(response.text)
        else:
            print ("Error reaching the server.")
            exit(1)
        return data

    def post_request(self,payload,url):
        response = requests.post(url, headers=self.header, json=payload,verify=False)
        if(response.status_code == 200 or response.status_code == 202):
            data = json.loads(response.text)
            return data
        else:
            print ("Error reaching the server.")
            print (response.text)
            exit(1)

    def post_request_raw(self,payload,url):
        response = requests.post(url, headers=self.header, json=payload,verify=False)
        if(response.status_code in [200, 202]):
            return response
        else:
            print ("Error reaching the server.")
            print (response.text)
            exit(1)

    
    def patch_request(self,payload,url):
        response = requests.patch(url, headers=self.header, json=payload,verify=False)
        if(response.status_code == 202):
            data = json.loads(response.text)
            return data
        elif(response.status_code == 200):
            return
        else:
            print ("Error reaching the server from patch.")
            print (response.text)
            exit(1)

    def get_poll_request(self, url, expected_status):
        response = self.get_request(url)
        while response['status'] in ['In Progress', 'IN_PROGRESS', 'Pending']:
            time.sleep(5)
            response = self.get_request(url)

        if response['status'] == expected_status:
            return response
        else:
            print('\033[91m Operation failed \033[00m', end='\n\n')
            exit(1)


    def poll_on_id(self,url,task):
        key = ''
        if(task):
            key = 'status'
        else:
            key = 'executionStatus'
        status = self.get_request(url)[key]
        while(status in ['In Progress','IN_PROGRESS','Pending']):
            response = self.get_request(url)
            status = response[key]
            time.sleep(10)
        if(task):
            return status
        if(status == 'COMPLETED'):
            return response['resultStatus']
        else:
            print ('Operation failed')
            exit(1)

    def poll_on_queries(self,url):
        response = self.get_request(url)
        status = response['queryInfo']['status']
        while(status in ['In Progress','IN_PROGRESS','Pending']):
            response = self.get_request(url)
            status = response['queryInfo']['status']
            time.sleep(10)
        if(status == 'COMPLETED'):
            return response['result']
        else:
            print ('Operation failed')
            exit(1)
    
    def delete_request(self,payload,url):
        response = requests.delete(url,json=payload,headers=self.header,verify=False)
        if(response.status_code == 202):
            data = json.loads(response.text)
            return data
        else:
            print ("Error reaching the server.")
            print (response.text)
            exit(1)
    
    def read_input(self, file):
        with open(file) as json_file:
            data = json.load(json_file)
        return data

    def print_validation_errors(self, url):
        validation_response = self.get_request(url)
        if "validationChecks" in validation_response:
            failed_tasks = list(
                filter(lambda x: x["resultStatus"] == "FAILED", validation_response["validationChecks"]))
            for failed_task in failed_tasks:
                self.printRed(failed_task['description'] + ' ' + 'failed')
                if "errorResponse" in failed_task and "message" in failed_task["errorResponse"]:
                    self.printRed(failed_task["errorResponse"]["message"])
                if "nestedValidationChecks" in failed_task:
                    for nested_task in failed_task["nestedValidationChecks"]:
                        if "errorResponse" in nested_task and "message" in nested_task["errorResponse"]:
                            self.printRed(nested_task["errorResponse"]["message"])

    def password_check(self, pwd, cannotbe = None):
        #rule: minlen = 8, maxlen = 32, at least 1 number, 1 upper, 1 lower, 1 special char
        minlen = 8
        maxlen = 32
        hasnum = True
        hasupper = True
        haslower =True
        hasspecial = True

        res = True

        if cannotbe is not None and pwd == cannotbe:
            self.print_error ("Password cannot be same as you have inputed")
            return False

        if len(pwd) < minlen:
            self.print_error ("Length should be at least {}".format(minlen))
            res = False
        elif len(pwd) > maxlen:
            self.print_error ("Length should be less than {}".format(maxlen))
            res = False

        if hasnum and not any(c.isdigit() for c in pwd):
            self.print_error ("Password should have at least one number")
            res = False
        if hasupper and not any(c.isupper() for c in pwd):
            self.print_error ("Password should have at least one upper case letter")
            res = False
        if haslower and not any(c.islower() for c in pwd):
            self.print_error ("Password should have at least one lower case letter")
            res = False

        if hasspecial and len(re.compile('[0-9 a-z A-Z]').sub('', pwd)) == 0:
            self.print_error ("Password should contain at least one special character")
            res = False

        return res

    def print_error(self, msg):
        RED = '\033[1;31m'
        TAIL = '\033[0m'
        head = RED + "Error:" + TAIL
        print("{}{}".format(head, msg))

    def valid_input(self, inputinfo, defaultvalue = None, validfunc = None, ext_args = None, is_password = False):
        while(True):
            if is_password:
                inputstr = getpass.getpass(inputinfo)
            else:
                inputstr = input(inputinfo)
            if len(str(inputstr).strip()) == 0 and defaultvalue is not None:
                return defaultvalue
            if validfunc is not None:
                checkresult = validfunc(inputstr) if ext_args is None else validfunc(inputstr, ext_args)
                if checkresult:
                    return inputstr
                else:
                    self.printRed('Unable to validate the input')
            else:
                break
        return inputstr

    def printRed(self, message):
        print("\033[91m {}\033[00m".format(message))

    def printGreen(self, message):
        print("\033[92m {}\033[00m".format(message))

    def printYellow(self, message):
        print("\033[93m {}\033[00m".format(message))

    def printCyan(self, message):
        print("\033[96m {}\033[00m".format(message))

    def printBold(self, message):
        print("\033[95m {}\033[00m".format(message))

    def valid_pwd_match(self, inputstr, ext_args):
        res = inputstr == ext_args
        if not res:
            self.print_error("Password doesn't match")
        return res
