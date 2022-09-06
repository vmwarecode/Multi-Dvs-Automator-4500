# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #

__author__ = 'jradhakrishna'

import time
from Utils.utils import Utils


class ClustersAutomator:
    def __init__(self, args):
        self.utils = Utils(args)
        self.hostname = args[0]
        self.utils.printGreen('Initializing Clusters Automator')

    def create_cluster(self, data):
        validations_url = 'https://'+self.hostname+'/v1/clusters/validations'
        response = self.utils.post_request(data, validations_url)
        self.utils.printGreen(
            'Validation started for import cluster operation. The validation id is: ' + response['id'])
        validate_poll_url = 'https://'+self.hostname+'/v1/clusters/validations/' + response['id']
        self.utils.printGreen ('Polling on validation api ' + validate_poll_url)
        time.sleep(10)
        validation_status = self.utils.poll_on_id(validate_poll_url, False)
        self.utils.printGreen('Validate cluster ended with status: ' + validation_status)
        if validation_status != 'SUCCEEDED':
            self.utils.printRed ('Validation Failed.')
            self.utils.print_validation_errors(validate_poll_url)
            exit(1)
        input("\033[1m Enter to import cluster..\033[0m")

        create_cluster_url = 'https://' + self.hostname + '/v1/clusters'
        response = self.utils.post_request(data, create_cluster_url)
        self.utils.printGreen(
            'Importing cluster, monitor the status of the task(task-id:' + response['id'] + ') from sddc-manager ui')
        # task_url = 'https://'+self.hostname+'/v1/tasks/' + response['id']
        # self.utils.printGreen('Create cluster ended with status: ' + self.utils.poll_on_id(task_url,True))

    def get_unmanaged_clusters(self, payload, domain_id):
        clusters_url = 'https://'+self.hostname+'/v1/domains/' + domain_id + '/clusters/queries'
        # self.utils.printGreen('\nGet queries api: ' + clusters_url)
        response = self.utils.post_request_raw(payload, clusters_url)
        return response

    def get_unmanaged_cluster(self, payload, domain_id, clustername):
        cluster_url = 'https://'+ self.hostname +'/v1/domains/' + domain_id + '/clusters/' + clustername + '/queries'
        # self.utils.printGreen('\nGet queries api: ' + cluster_url + ' payload:' + json.dumps(payload))
        time.sleep(20)
        response = self.utils.post_request_raw(payload, cluster_url)
        return response

    def get_cluster_with_host_details(self, domain_id, clusterName):
        post_url = 'http://' + self.hostname + '/domainmanager/vxrail/vidomains/' + domain_id + '/cluster/queries'
        data = {"clusterName": clusterName}
        response = self.utils.post_request(data, post_url)

        get_url = 'http://' + self.hostname + '/domainmanager/vxrail/vidomains/requests/' + response['id']
        get_response = self.utils.get_poll_request(get_url, 'MARKED_FOR_EVICTION')
        return get_response

    def poll_queries(self, url):
        queries_url = url
        time.sleep(15)
        response = self.utils.poll_on_queries(queries_url)
        return response






