# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #

__author__ = 'jradhakrishna'

from Utils.utils import Utils
import getpass

class VxRailAuthAutomator:
    def __init__(self, args):
        self.utils = Utils(args)
        self.description = "VxRail Manager authentication details"

    def main_func(self):
        three_line_separator = ['', '', '']
        self.utils.printCyan("Please input VxRail Manager's preconfigure root credentials")
        root_user = "root"
        root_password =self.__handle_password_input()

        print(*three_line_separator, sep='\n')

        self.utils.printCyan("Please input VxRail Manager's preconfigured admin credentials")
        admin_user =  self.utils.valid_input("\033[1m Enter username (mystic): \033[0m", "mystic")
        admin_password = self.__handle_password_input()

        print(*three_line_separator, sep='\n')

        return {
            "rootCredentials": self.__to_credential_obj(root_user, root_password),
            "adminCredentials": self.__to_credential_obj(admin_user, admin_password)
        }

    def __to_credential_obj(self, user, pwd):
        return {
            "credentialType" : "SSH",
            "username" : user,
            "password" : pwd
        }

    def __valid_password(self, inputstr):
        return self.utils.password_check(inputstr)

    def __valid_pwd_match(self, inputstr, ext_args):
        res = inputstr == ext_args
        if not res:
            self.utils.print_error("Password doesn't match")
        return res

    def __handle_password_input(self):
        while(True):
            thepwd = getpass.getpass("\033[1m Enter password: \033[0m")
            confirmpwd = getpass.getpass("\033[1m Confirm password: \033[0m")
            if thepwd != confirmpwd:
                self.utils.printRed("Passwords don't match")
            else:
                return thepwd
