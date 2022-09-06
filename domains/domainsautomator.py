# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #
#  Description: Domain related operations

__author__ = 'jradhakrishna'

from Utils.utils import Utils
import time



class DomainsAutomator:
    def __init__(self, args):
        self.utils = Utils(args)
        self.hostname = args[0]
        self.utils.printGreen('Initializing Domains Automator')

    def create_workload_domain(self, payload):
        # validations
        validations_url = 'https://' + self.hostname + '/v1/domains/validations/creations'
        print ('Validating the input....')
        response = self.utils.post_request(payload, validations_url)
        if (response['resultStatus'] != 'SUCCEEDED'):
            print ('Validation Failed.')
            exit(1)

        # Domain Creation
        domain_creation_url = self.hostname + '/v1/domains'
        response = self.utils.post_request(payload, domain_creation_url)
        print ('Creating Domain...')

        task_url = 'https://' + self.hostname + '/v1/tasks/' + response['id']
        print ("Domain creation task completed with status:  " + self.utils.poll_on_id(task_url, True))

    def update_workload_domain(self, payload, domain_id):
        # validations
        validations_url = 'https://' + self.hostname + '/v1/domains/' + domain_id + '/validations '
        self.utils.printGreen('Validating the input....')
        response = self.utils.post_request(payload, validations_url)
        self.utils.printGreen(
            'Validation started for import cluster operation. The validation id is: ' + response['id'])
        validate_poll_url = 'https://' + self.hostname + '/v1/domains/validations/' + response['id']
        self.utils.printGreen('Polling on validation api ' + validate_poll_url)
        time.sleep(10)
        validation_status = self.utils.poll_on_id(validate_poll_url, False)
        self.utils.printGreen('Validate domain ended with status: ' + validation_status)
        if validation_status != 'SUCCEEDED':
            self.utils.printRed('Validation Failed.')
            self.utils.print_validation_errors(validate_poll_url)
            exit(1)

        # Domain Update
        input("\033[1m Enter to import cluster..\033[0m")
        domain_creation_url = 'https://' + self.hostname + '/v1/domains/' + domain_id
        response = self.utils.patch_request(payload, domain_creation_url)
        self.utils.printGreen(
            'Importing cluster, monitor the status of the task(task-id:' + response['id'] + ') from sddc-manager ui')
        # task_url = 'https://' + self.hostname + '/v1/tasks/' + response['id']
        # print ("Domain creation task completed with status:  " + self.utils.poll_on_id(task_url, True))

    def get_domains(self):
        # get domains
        domains_url = 'https://' + self.hostname + '/v1/domains'
        self.utils.printGreen('Getting the domains..')
        response = self.utils.get_request(domains_url)
        return response

    def get_domains_details(self, id):
        # get domains
        domains_details_url = 'http://' + self.hostname + '/inventory/domains/' + id + '/inventory'
        self.utils.printGreen('Getting the domains details ..')
        response = self.utils.get_request(domains_details_url)
        return response



