# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #

__author__ = 'jradhakrishna'

from Utils.utils import Utils

class LicenseAutomator:
    def __init__(self, args):
        self.utils = Utils(args)
        self.description = "Select license"
        self.hostname = args[0]

    def main_func(self, ignoreVsanLicense):
        lcs = self.__get_licenses()
        selected = {}
        three_line_separator = ['', '', '']

        for k in lcs.keys():
            if k == "VSAN" and ignoreVsanLicense :
                continue
            lcsls = lcs[k]
            self.utils.printCyan("Please choose a {} license:".format(k))
            ct = 0
            lcsmap = {}
            for onelcs in lcsls:
                ct += 1
                self.utils.printBold("{}) {}".format(ct, self.__output_license_info(onelcs)))
                lcsmap[str(ct)] = onelcs
            selected[k] = lcsmap[self.__valid_option(input("\033[1m Enter your choice(number): \033[0m"), lcsmap.keys()) ]["key"]
            print(*three_line_separator, sep='\n')
        return {"licenseKeys":selected}

    def __output_license_info(self, licenseobj):
        return "{} ({})".format(licenseobj["key"], licenseobj["validity"])

    def __get_licenses(self):
        self.utils.printGreen("Getting license information...")
        url = 'https://'+self.hostname+'/v1/license-keys?productType=VSAN,NSXT'
        response = self.utils.get_request(url)
        vsankeys = [{"key":ele["key"], "validity":ele["licenseKeyValidity"]["licenseKeyStatus"]} for ele in response["elements"] if ele["productType"] == "VSAN"]
        nsxtkeys = [{"key":ele["key"], "validity":ele["licenseKeyValidity"]["licenseKeyStatus"]} for ele in response["elements"] if ele["productType"] == "NSXT"]
        return {"VSAN":vsankeys, "NSX-T": nsxtkeys}

    def __valid_option(self, inputstr, choices):
        choice = str(inputstr).strip().lower()
        if choice in choices:
            return choice
        self.utils.printYellow("**Use first choice by default")
        return list(choices)[0]