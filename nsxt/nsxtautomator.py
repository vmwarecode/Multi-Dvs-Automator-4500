# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #

__author__ = 'jradhakrishna'

import ipaddress
import time
import re
from Utils.utils import Utils
import subprocess
import sys
import getpass


class NSXTAutomator:
    def __init__(self, args):
        self.utils = Utils(args)
        self.description = "NSX-T instance deployment"
        self.hostname = args[0]

    # If current handling domain is management domain, is_primary must be False
    def main_func(self, selected_domain_id, is_primary=True, is_3x_4x_migration_env=False):
        three_line_separator = ['', '', '']
        nsxt_instances = self.__get_nsxt_instances(selected_domain_id, is_primary)
        if is_primary:
            if len(nsxt_instances) > 0:
                self.utils.printCyan("Please choose NSX-T instance option:")
                self.utils.printBold("1) Create new NSX-T instance (default)")
                self.utils.printBold("2) Use existing NSX-T instance")
                theoption = self.utils.valid_input("\033[1m Enter your choice(number): \033[0m", "1",
                                                   self.__valid_option, ["1", "2"])
            else:
                self.utils.printYellow("** No shared NSX-T instance was found, you need to create a new one")
                theoption = "1"
        else:
            if len(nsxt_instances) == 0:
                # In a common situation, this is not possible
                self.utils.printRed("No shared NSX-T instance discovered in current domain")
                input("Enter to exit ...")
                sys.exit(1)
            else:
                theoption = "2"

        print(*three_line_separator, sep='\n')

        if theoption == "1":
            return self.option1_new_nsxt_instance(is_3x_4x_migration_env)

        return self.option2_existing_nsxt(nsxt_instances, is_3x_4x_migration_env)

    """
        In case of secondary cluster, the NSX-T cluster has to be the same as that of the primary cluster.
        We don’t need to provide an option to create a new NSX-T cluster or list the NSX-T clusters that are not mapped to the primary cluster.
        We can identify the NSX-T cluster based on the domain ID (as provided below).

        In case of primary cluster, the NSX-T cluster could be a new cluster or an existing one.
        List only the NSX-T clusters that have the property isShareable as TRUE.
        The management NSX-T cluster is dedicated to management domain and will have the isShareable property set to FALSE.
    """

    def __get_nsxt_instances(self, selected_domain_id, is_primary=True):
        self.utils.printGreen("Getting shared NSX-T cluster information...")
        url = 'https://' + self.hostname + '/v1/nsxt-clusters'
        response = self.utils.get_request(url)
        nsxinstances = []
        for oneins in response["elements"]:
            if is_primary and oneins["isShareable"]:
                nsxinstances.append(oneins)
            elif not is_primary:
                domainids = [onedomain["id"] for onedomain in oneins["domains"]]
                if selected_domain_id in domainids:
                    nsxinstances.append(oneins)
        return nsxinstances

    def __get_static_ip_pool(self, nsxt_cluster_id):
        self.utils.printGreen("Getting Static IP Pool information...")
        url = 'https://' + self.hostname + '/v1/nsxt-clusters/' + nsxt_cluster_id + '/ip-address-pools'
        response = self.utils.get_request(url)
        ip_address_pools = []
        for element in response['elements']:
            ip_address_pools.append(element)
        return ip_address_pools

    def __generate_ip_address_pool_ranges(self, inputstr):
        ip_ranges = [x.strip() for x in inputstr.split(',')]
        res = []
        for ip_range in ip_ranges:
            ips = ip_range.split('-')
            res.append({"start": ips[0], "end": ips[1]})
        return res

    def check_overlap_subnets(self, cidrs, input_cidr):
        if cidrs:
            for c in cidrs:
                if ipaddress.IPv4Network(input_cidr).overlaps(ipaddress.IPv4Network(c)):
                    self.utils.printRed(
                        'Overlapping subnet {} with {}. Please enter valid subnet details...'.format(input_cidr, c))
                    return True
        return False

    def input_subnet(self, subnets, cidrs, count):
        three_line_separator = ['', '', '']
        print(*three_line_separator, sep='\n')
        self.utils.printCyan("Subnet #{}".format(count))
        cidr = self.utils.valid_input("\033[1m Enter CIDR: \033[0m", None, self.__valid_cidr)
        self.utils.printYellow("** Multiple IP Ranges are supported by comma separated")
        ip_ranges = self.utils.valid_input("\033[1m Enter IP Range: \033[0m", None, self.__valid_ip_ranges)
        gateway_ip = self.utils.valid_input("\033[1m Enter Gateway IP: \033[0m", None, self.__valid_ip)

        if self.check_overlap_subnets(cidrs, cidr):
            self.input_subnet(subnets, cidrs, count)
        else:
            cidrs.append(cidr)
            subnet = {
                "ipAddressPoolRanges": self.__generate_ip_address_pool_ranges(ip_ranges),
                "cidr": cidr,
                "gateway": gateway_ip
            }
            subnets.append(subnet)
            print(*three_line_separator, sep='\n')
            select_option = input("\033[1m Do you want to add another subnet ? (Enter 'yes' or 'no'): \033[0m")
            if select_option.lower() == 'yes':
                self.input_subnet(subnets, cidrs, count + 1)
            return subnets

    def create_static_ip_pool(self):
        self.utils.printCyan("Create New Static IP Pool")
        while True:
            pool_name = input("\033[1m Enter Pool Name: \033[0m")
            reg = "^[a-zA-Z0-9-_]+$"
            match_re = re.compile(reg)
            result = re.search(match_re, pool_name)
            if not result:
                self.utils.printRed("Invalid IP pool address name. The IP address pool name should contain only "
                                    "alphanumeric characters along with '-' or '_' without spaces")
            else:
                break
        description = input("\033[1m Enter Description(Optional): \033[0m")
        ip_address_pool_spec = {
            "name": pool_name,
            "subnets": self.input_subnet([], [], count=1)
        }
        if description:
            ip_address_pool_spec.update({"description": description})
        return ip_address_pool_spec

    def __prepare_ip_address_pool(self, ip_address_pool):
        ip_address_pool_spec = {
            "name": ip_address_pool['name']
        }
        return ip_address_pool_spec

    def option2_existing_nsxt(self, nsxt_instances, is_3x_4x_migration_env=False):
        three_line_separator = ['', '', '']
        geneve_vlan = self.utils.valid_input("\033[1m Enter Geneve vLAN ID (0-4096): \033[0m ", None, self.__valid_vlan)
        print(*three_line_separator, sep='\n')

        self.utils.printCyan("Please select one NSX-T instance")
        ct = 0
        nsxt_map = {}
        for nsxt_inst in nsxt_instances:
            idx = str(ct + 1)
            ct += 1
            nsxt_map[idx] = nsxt_inst
            self.utils.printBold("{0}) NSX-T vip: {1}".format(idx, nsxt_inst["vipFqdn"]))

        choiceidx = self.utils.valid_input("\033[1m Enter your choice(number): \033[0m", None, self.__valid_option,
                                           nsxt_map.keys())
        selected_ins = nsxt_map[choiceidx]

        print(*three_line_separator, sep='\n')
        selected_option = "1"
        if not is_3x_4x_migration_env:
            self.utils.printCyan("Please choose IP Allocation for TEP IPs option:")
            self.utils.printBold("1) DHCP (default)")
            self.utils.printBold("2) Static IP Pool")
            selected_option = self.utils.valid_input("\033[1m Enter your choice(number): \033[0m", "1", self.__valid_option,
                                                    ["1", "2"])
        print(*three_line_separator, sep='\n')

        ip_address_pool_spec = None
        if selected_option == "2":
            self.utils.printCyan("Select the option for Static IP Pool:")
            self.utils.printBold("1) Create New Static IP Pool(default)")
            self.utils.printBold("2) Re-use an Existing Static Pool")
            static_ip_pool_option = self.utils.valid_input("\033[1m Enter your choice(number): \033[0m", "1",
                                                           self.__valid_option,
                                                           ["1", "2"])
            print(*three_line_separator, sep='\n')

            if static_ip_pool_option == "1":
                ip_address_pool_spec = self.create_static_ip_pool()
            elif static_ip_pool_option == "2":
                ip_address_pools = self.__get_static_ip_pool(selected_ins["id"])
                print(*three_line_separator, sep='\n')
                if not ip_address_pools:
                    self.utils.printRed("No existing Static IP Pools are getting discovered...")
                    input("\033[1m Enter to exit ...\033[0m")
                    sys.exit(1)
                self.utils.printCyan("Please select one static ip pool:")
                self.utils.printBold("-----Pool Name-------------------Subnets---------------------------Available IPs--")
                self.utils.printBold("----------------------------------------------------------------------------------")
                count = 0
                ip_pool_map = {}
                for ip_address_pool in ip_address_pools:
                    count += 1
                    pool_name = '{}) {} : '.format(count, ip_address_pool['name'])
                    self.utils.printBold(
                        '{} Static/Block Subnets {}: {}'.format(pool_name, 30 * ' ', ip_address_pool['availableIpAddresses']))
                    if ip_address_pool['staticSubnets']:
                        self.utils.printBold('{} Static Subnets '.format(len(pool_name) * ' '))
                        print("{}\033[36m  -----CIDR-------------IP Ranges-----------".format(len(pool_name) * ' '))
                        for static_subnet in ip_address_pool['staticSubnets']:
                            ip_ranges = []
                            for ip_range in static_subnet['ipAddressPoolRanges']:
                                ip_ranges.append('{}-{}'.format(ip_range['start'], ip_range['end']))
                            print("\033[36m  {} {} : {}".format(len(pool_name) * ' ', static_subnet['cidr'], ip_ranges))

                    if 'blockSubnets' in ip_address_pool:
                        self.utils.printBold('{} Block Subnets '.format(len(pool_name) * ' '))
                        print("{}\033[36m  -----CIDR-------------Size----------------".format(len(pool_name) * ' '))
                        for block_subnet in ip_address_pool['blockSubnets']:
                            print("\033[36m  {} {} : {}".format(len(pool_name) * ' ', block_subnet['cidr'],
                                                                     block_subnet['size']))
                    ip_pool_map[str(count)] = self.__prepare_ip_address_pool(ip_address_pool)
                    print('\n')
                choice = self.utils.valid_input("\033[0;1m Enter your choice(number): \033[0m", None,
                                                self.__valid_option,
                                                ip_pool_map.keys())
                ip_address_pool_spec = ip_pool_map[choice]
            print(*three_line_separator, sep='\n')
        nsxTSpec = {
            "nsxManagerSpecs": [
            ],
            "vip": selected_ins["vip"],
            "vipFqdn": selected_ins["vipFqdn"]
        }
        for nsxnode in selected_ins["nodes"]:
            nsxTSpec["nsxManagerSpecs"].append(
                {
                    "name": nsxnode["name"],
                    "networkDetailsSpec": {
                        "dnsName": nsxnode["fqdn"],
                        "ipAddress": nsxnode.get("ipAddress")
                    }
                }
            )

        if ip_address_pool_spec is not None:
            nsxTSpec.update({"ipAddressPoolSpec": ip_address_pool_spec})

        return {"nsxTSpec": nsxTSpec, "geneve_vlan": geneve_vlan}

    def option1_new_nsxt_instance(self, is_3x_4x_migration_env=False):
        three_line_separator = ['', '', '']
        geneve_vlan = self.utils.valid_input("\033[1m Enter Geneve vLAN ID (0-4096): \033[0m", None, self.__valid_vlan)
        admin_password = self.__handle_password_input()
        print(*three_line_separator, sep='\n')

        self.utils.printCyan("Please Enter NSX-T VIP details")
        nsxt_vip_fqdn = self.utils.valid_input("\033[1m FQDN (IP address will be fetched from DNS): \033[0m", None,
                                               self.__valid_fqdn)
        nsxt_gateway = self.utils.valid_input("\033[1m Gateway IP address: \033[0m", None, self.__valid_ip)
        nsxt_netmask = self.utils.valid_input("\033[1m Subnet mask (255.255.255.0): \033[0m", "255.255.255.0",
                                              self.__valid_ip)
        print(*three_line_separator, sep='\n')

        nsxt_1_fqdn = self.utils.valid_input("\033[1m Enter FQDN for 1st NSX-T Manager: \033[0m",
                                             None, self.__valid_fqdn)
        print(*three_line_separator, sep='\n')

        nsxt_2_fqdn = self.utils.valid_input("\033[1m Enter FQDN for 2nd NSX-T Manager: \033[0m",
                                             None, self.__valid_fqdn)
        print(*three_line_separator, sep='\n')

        nsxt_3_fqdn = self.utils.valid_input("\033[1m Enter FQDN for 3rd NSX-T Manager: \033[0m",
                                             None, self.__valid_fqdn)
        print(*three_line_separator, sep='\n')
        selected_option = "1"
        if not is_3x_4x_migration_env:
            self.utils.printCyan("Please choose IP Allocation for TEP IPs option:")
            self.utils.printBold("1) DHCP (default)")
            self.utils.printBold("2) Static IP Pool")
            selected_option = self.utils.valid_input("\033[1m Enter your choice(number): \033[0m", "1", self.__valid_option,
                                                    ["1", "2"])

        ip_address_pool_spec = None
        if selected_option == "2":
            print(*three_line_separator, sep='\n')
            ip_address_pool_spec = self.create_static_ip_pool()
        print(*three_line_separator, sep='\n')

        nsxTSpec = {
            "nsxManagerSpecs": [
                self.__to_nsx_manager_obj(nsxt_1_fqdn, nsxt_gateway, nsxt_netmask),
                self.__to_nsx_manager_obj(nsxt_2_fqdn, nsxt_gateway, nsxt_netmask),
                self.__to_nsx_manager_obj(nsxt_3_fqdn, nsxt_gateway, nsxt_netmask)
            ],
            "vip": self.__nslookup_ip_from_dns(nsxt_vip_fqdn),
            "vipFqdn": nsxt_vip_fqdn,
            "nsxManagerAdminPassword": admin_password
        }

        if ip_address_pool_spec is not None:
            nsxTSpec.update({"ipAddressPoolSpec": ip_address_pool_spec})

        return {"nsxTSpec": nsxTSpec, "geneve_vlan": geneve_vlan}

    def __to_nsx_manager_obj(self, fqdn, gateway, netmask):
        ip = self.__nslookup_ip_from_dns(fqdn)
        return {
            "name": fqdn.split('.')[0],
            "networkDetailsSpec": {
                "ipAddress": ip,
                "dnsName": fqdn,
                "gateway": gateway,
                "subnetMask": netmask
            }
        }

    def __valid_option(self, inputstr, choices):
        choice = str(inputstr).strip().lower()
        if choice in choices:
            return choice
        self.utils.printYellow("**Use first choice by default")
        return list(choices)[0]

    def __valid_password(self, inputstr):
        return self.utils.password_check(inputstr)

    def __valid_vlan(self, inputstr):
        res = True
        if not str(inputstr).isdigit():
            res = False
        res = (int(inputstr) >= 0 and int(inputstr) <= 4096)
        if not res:
            self.utils.printRed("VLAN must be a number in between 0-4096")
        return res

    def __valid_fqdn(self, inputstr):
        res = True
        if len(inputstr) <= 3 or len(inputstr) > 255:
            res = False
        elif "." not in inputstr:
            res = False
        elif inputstr[0] == "." or inputstr[-1] == ".":
            res = False
        else:
            segmatch = re.compile("[0-9 a-z A-Z _ -]")
            res = all((len(segmatch.sub('', oneseg)) == 0 and len(oneseg) > 0) for oneseg in inputstr.split("."))
        if not res:
            self.utils.printRed("FQDN format is not correct")
        else:
            self.utils.printGreen("Resolving IP from DNS...")
            theip = self.__nslookup_ip_from_dns(inputstr)
            if theip is not None:
                self.utils.printGreen("Resolved IP address: {}".format(theip))
            else:
                res = False
                self.utils.printRed("Hasn't found matched IP from DNS")

        return res

    def __valid_ip(self, inputstr):
        res = re.compile("(\d+\.\d+\.\d+\.\d+)$").match(inputstr) is not None and all(
            (int(seg) >= 0 and int(seg) <= 255) for seg in inputstr.split("."))
        if not res:
            self.utils.printRed("IP format is not correct")
        return res

    def __valid_cidr(self, inputstr):
        pattern = r'(\d+\.\d+\.\d+\.\d+)\/([0-9]|[1-2][0-9]|3[0-2])$'
        res = re.match(pattern, inputstr) is not None and all((0 <= int(seg) <= 255)
                                                              for seg in
                                                              re.search(pattern, inputstr).group(1).split("."))
        if not res:
            self.utils.printRed("CIDR format is not correct")
        return res

    # IP Ranges will be in form of eg.10.0.0.1-10.0.0.10, 10.0.0.20-10.0.0.30
    def __valid_ip_ranges(self, inputstr):
        ip_ranges: List[Any] = [x.strip() for x in inputstr.split(',')]
        for ip_range in ip_ranges:
            try:
                start_ip, end_ip = ip_range.split('-')
            except ValueError:
                self.utils.printRed("IP Range format is not correct")
                return None
            res = self.__valid_ip(start_ip) and self.__valid_ip(end_ip)
            if not res:
                return res
        return True

    def __nslookup_ip_from_dns(self, fqdn):
        cmd = "nslookup {}".format(fqdn)
        sub_popen = subprocess.Popen(cmd,
                                     shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        output, err = sub_popen.communicate()
        if sub_popen.returncode > 0:
            return None

        thenext = False
        # byte feature only supported in python 3
        for aline in output.decode('utf8').split("\n"):
            if thenext and str(aline).lower().startswith("address:"):
                return aline.split(":")[-1].strip()
            if str(aline).lower().startswith("name:"):
                tail = aline.split(":")[-1].strip()
                if tail == fqdn:
                    thenext = True
        return None

    def __handle_password_input(self):
        while (True):
            thepwd = getpass.getpass("\033[1m Enter Admin password: \033[0m")
            confirmpwd = getpass.getpass("\033[1m Confirm Admin password: \033[0m")
            if thepwd != confirmpwd:
                self.utils.printRed("Passwords don't match")
            else:
                return thepwd
