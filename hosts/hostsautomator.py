# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #

__author__ = 'jradhakrishna'

import getpass
from Utils.utils import Utils

ESXI_TYPE = 'ESXi'
VXRAIL_MANAGER_TYPE = 'VIRTUAL_MACHINE'

class HostsAutomator:
    def __init__(self, args):
        self.utils = Utils(args)
        self.password_map = {}

    def main_func(self, hosts_fqdn):
        three_line_separator = ['', '', '']
        self.utils.printCyan("Below hosts are discovered. Enter the password for them:")
        hostls = []
        for idx, element in enumerate(hosts_fqdn):
            self.utils.printBold("{}) {}".format(idx + 1, element['hostName']))
            hostls.append(element['hostName'])

        print(*three_line_separator, sep='\n')

        self.utils.printCyan("Please choose password option:")
        self.utils.printBold("1) Input one password that is applicable to all the hosts (default)")
        self.utils.printBold("2) Input password individually for each host")
        theoption = self.utils.valid_input("\033[1m Enter your choice(number): \033[0m", "1", self.__valid_option, ["1", "2"])

        print(*three_line_separator, sep='\n')
        if theoption == "1":
            self._option1(hostls)
        else:
            self._option2(hostls)

    def _option1(self, hostls):
        three_line_separator = ['', '', '']
        pwd = self.__handle_password_input()
        for hnm in hostls:
            self.password_map[hnm] = pwd
        print(*three_line_separator, sep='\n')

    def _option2(self, hostls):
        three_line_separator = ['', '', '']
        for hnm in hostls:
            self.utils.printCyan("Input root password of host {}".format(hnm))
            self.password_map[hnm] = self.__handle_password_input()
            print(*three_line_separator, sep='\n')


    def __valid_option(self, inputstr, choices):
        choice = str(inputstr).strip().lower()
        if choice in choices:
            return choice
        self.utils.printYellow("**Use first choice by default")
        return list(choices)[0]

    def __handle_password_input(self):
        while(True):
            thepwd = getpass.getpass("\033[1m Enter root password: \033[0m")
            confirmpwd = getpass.getpass("\033[1m Confirm password: \033[0m")
            if thepwd != confirmpwd:
                self.utils.printRed("Passwords don't match")
            else:
                return thepwd

    def get_ssh_thumbprints(self, hostsSpec, domain_id, vxrm_fqdn, vxrm_admin_username, vxrm_admin_password):
        post_url = 'http://localhost/domainmanager/vxrail/hosts/unmananged/fingerprint'
        payload = {
            "sshFingerprints": [],
            "domainId": domain_id
        }
        for host in hostsSpec:
            payload['sshFingerprints'].append(
                {'fqdn': host['hostName'], 'userName': 'root', 'password': self.password_map[host['hostName']],
                 'type': ESXI_TYPE})

        payload['sshFingerprints'].append(
            {'fqdn': vxrm_fqdn, 'userName': vxrm_admin_username, 'password': vxrm_admin_password,
             'type': VXRAIL_MANAGER_TYPE})

        response = self.utils.post_request(payload, post_url)

        get_url = 'http://localhost/domainmanager/vxrail/hosts/requests/' + response['id']
        thumbprints_response = self.utils.get_poll_request(get_url, 'COMPLETED')

        fqdn_to_thumbprint_dict = {}
        for thumbprint_response in thumbprints_response['sshFingerprints']:
            fqdn_to_thumbprint_dict[thumbprint_response['id']] = thumbprint_response['fingerPrint']

        self.display_and_confirm_ssh_thumbprints(fqdn_to_thumbprint_dict, vxrm_fqdn)

        return fqdn_to_thumbprint_dict

    def display_and_confirm_ssh_thumbprints(self, fqdn_to_thumbprint_dict, vxrm_fqdn):
        self.utils.printCyan('Please confirm SSH Thumbprint of Hosts and VxRail Manager:')
        self.utils.printBold('-----------FQDN--------------------------Fingerprint------------------------------Type------------')
        self.utils.printBold('--------------------------------------------------------------------------------------------------')
        for fqdn_to_thumbprint in fqdn_to_thumbprint_dict:
            if fqdn_to_thumbprint == vxrm_fqdn:
                type = VXRAIL_MANAGER_TYPE
            else:
                type = ESXI_TYPE
            self.utils.printBold('{} : {} : {}'.format(fqdn_to_thumbprint, fqdn_to_thumbprint_dict[fqdn_to_thumbprint], type))
        selected_option = input("\033[1m Enter your choice ('yes' or 'no') : \033[0m")
        if selected_option.lower() == 'no':
            self.utils.printRed('Fingerprints are not confirmed so exiting...')
            exit(1)
        elif selected_option.lower() == 'yes':
            return
        else:
            self.utils.printRed('Please enter valid option')
            exit(1)

    def populatehostSpec(self, isExistingDvs = True, hostsSpec = None, vmNics = None, fqdn_to_thumbprint_dict = None):
        uname = "root"
        temp_hosts_spec = []
        for element in hostsSpec:
            hostSpec = {}
            hostSpec['ipAddress'] = element['ipAddress']
            hostSpec['hostName'] = element['hostName']
            hostSpec['username'] = uname
            hostSpec['password'] = self.password_map[element['hostName']]
            hostSpec['sshThumbprint'] = fqdn_to_thumbprint_dict.get(element['hostName'])
            if not isExistingDvs:
                hostSpec['hostNetworkSpec']= {
                    "vmNics": vmNics
                }
            temp_hosts_spec.append(hostSpec)
        return temp_hosts_spec