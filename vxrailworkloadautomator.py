# Copyright 2020 VMware, Inc.  All rights reserved. -- VMware Confidential  #

__author__ = 'jradhakrishna'

import time
import json
import copy
import getpass
import collections.abc
from Utils.utils import Utils
from domains.domainsautomator import DomainsAutomator
from clusters.clustersautomator import ClustersAutomator
from nsxt.nsxtautomator import NSXTAutomator
from vxrailManager.vxrailauthautomator import VxRailAuthAutomator
from license.licenseautomator import LicenseAutomator
from hosts.hostsautomator import HostsAutomator

MASKED_KEYS = ['password', 'nsxManagerAdminPassword']
UNMANAGED_CLUSTERS_CRITERION = 'UNMANAGED_CLUSTERS_IN_VCENTER'
UNMANAGED_CLUSTER_CRITERION = 'UNMANAGED_CLUSTER_IN_VCENTER'
MATCHING_VMNIC_CRITERION = 'UNMANAGED_CLUSTER_IN_VCENTER_MATCHING_PNICS_ACROSS_HOSTS'
REQ_VCF_VER = ['4.5']


class VxRaiWorkloadAutomator:
    def __init__(self):

        args = []
        args.append("localhost")
        args.append(input("\033[1m Enter the SSO username: \033[0m"))
        args.append(getpass.getpass("\033[1m Enter the SSO password: \033[0m"))
        self.utils = Utils(args)
        self.utils.printGreen('Welcome to VxRail Workload Automator')
        self.domains = DomainsAutomator(args)
        self.hosts = HostsAutomator(args)
        self.clusters = ClustersAutomator(args)
        self.nsxt = NSXTAutomator(args)
        self.vxrailmanager = VxRailAuthAutomator(args)
        self.licenses = LicenseAutomator(args)
        self.hostname = args[0]

    def let_user_pick(self, domain_selection_text, options):
        self.utils.printCyan(domain_selection_text)
        for idx, element in enumerate(options):
            self.utils.printBold("{}) {}".format(idx + 1, element['name']))
        while (True):
            inputstr = input("\033[1m Enter your choice(number): \033[0m")
            try:
                if 0 < int(str(inputstr).strip()) <= len(options):
                    return int(inputstr) - 1
                else:
                    inputstr = input(
                        "\033[1m Wrong input, Please input an option between 1(included) and {0}(included): \033[0m".format(
                            str(len(options))))
                    if 0 < int(str(inputstr).strip()) <= len(options):
                        return int(inputstr) - 1
            except:
                print("\033[1m Input a number between 1(included) and {0}(included)\033[0m".format(str(len(options))))

    def populatenetworkSpec(self, isExistingDvs=True, existingDvs=None, new_Dvs=None, nsxSpec=None, isPrimary=True):
        tempDvsSpec = {}
        tempDvsSpec['vdsSpecs'] = []
        if isExistingDvs:
            tempDvsSpec['vdsSpecs'].append(existingDvs)
        elif isPrimary and not isExistingDvs:
            tempDvsSpec['vdsSpecs'].append(new_Dvs)
        elif not isPrimary and not isExistingDvs:
            tempDvsSpec['vdsSpecs'].append(new_Dvs)

        tempDvsSpec['nsxClusterSpec'] = {
            "nsxTClusterSpec": {
                "geneveVlanId": int(nsxSpec["geneve_vlan"])
            }
        }
        if not isPrimary and 'ipAddressPoolSpec' in nsxSpec['nsxTSpec']:
            tempDvsSpec['nsxClusterSpec']['nsxTClusterSpec'] \
                .update({"ipAddressPoolSpec": nsxSpec["nsxTSpec"]["ipAddressPoolSpec"]})
        return tempDvsSpec

    def populatevxrmfqdn(self, domain_id, cluster_name):
        cluster_details = self.clusters.get_cluster_with_host_details(domain_id, cluster_name)
        vxrm_fqdn = None
        for vxrail_cluster_spec in cluster_details['vxRailClustersSpec']:
            if vxrail_cluster_spec['clusterName'] == cluster_name:
                vxrm_fqdn = vxrail_cluster_spec['vxrmFqdn']
        return vxrm_fqdn

    def populatehostSpec(self, isExistingDvs = True, hostsSpec = None, vmNics = None, uname = 'root', password = None):
        temp_hosts_spec = []
        for element in hostsSpec:
            hostSpec = {}
            hostSpec['ipAddress'] = element['ipAddress']
            hostSpec['hostName'] = element['hostName']
            hostSpec['username'] = uname
            hostSpec['password'] = password
            if not isExistingDvs:
                hostSpec['hostNetworkSpec']= {
                    "vmNics": vmNics
                }
            temp_hosts_spec.append(hostSpec)
        return temp_hosts_spec

    def populatensxtSpec(self, nsxt_payload = None, licenses_payload = None):
        nsxtSpec = nsxt_payload["nsxTSpec"]
        nsxtSpec["licenseKey"] = licenses_payload['licenseKeys']['NSX-T']
        return nsxtSpec

    def maskPasswords(self, obj):
        for k, v in obj.items():
            if isinstance(v, collections.abc.Mapping):
                obj[k] = self.maskPasswords(v)
            elif isinstance(v, list):
                for elem in v:
                    if isinstance(elem, dict) or isinstance(elem, list):
                        self.maskPasswords(elem)
            elif k in MASKED_KEYS:
                obj[k] = '*******'
            else:
                obj[k] = v
        return obj

    def getSystemDvs(self, dvsSpecs, dataStoreType):
        supported_pgs_for_datastore = {
            'VSAN': {'MANAGEMENT', 'VSAN', 'VMOTION'},
            'FC': {'MANAGEMENT', 'VMOTION'}
        }
        if len(dvsSpecs) > 0 :
            for dvs in dvsSpecs:
                if "portGroupSpecs" in dvs and len(dvs["portGroupSpecs"]) > 0:
                    available_pgs =set()
                    for pg in dvs["portGroupSpecs"]:
                        if "transportType" in pg:
                            available_pgs.add(pg["transportType"])
            supported_pgs = supported_pgs_for_datastore.get(dataStoreType)
            if supported_pgs.issubset(available_pgs):
                return dvs
        return None

    def check_sddc_manager_version(self):
        url = 'https://' + self.hostname + '/v1/sddc-managers'
        sddc_json = self.utils.get_request(url)
        sddc_ver = None
        for domain in sddc_json['elements']:
            sddc_ver = domain['version'].split("-")[0]
        for req_ver in REQ_VCF_VER:
            if sddc_ver is not None and sddc_ver.startswith(req_ver):
                return
        print('\033[91m Fetched VCF version is {} which is not matching with required version {}'.format(sddc_ver,REQ_VCF_VER))
        print('\033[91m Please make sure the VCF version should be {}'.format(REQ_VCF_VER))
        exit(1)

    @property
    def initApp(self):
        self.check_sddc_manager_version()
        #Get domains
        domains = self.domains.get_domains()
        domains_user_selection = list(map(lambda x: {"name": x['name'], "id": x['id']}, domains["elements"]))
        three_line_separator = ['', '', '']
        print(*three_line_separator, sep='\n')
        domain_selection_text = "Please choose the domain to which cluster has to be imported:"
        domain_index = self.let_user_pick(domain_selection_text, domains_user_selection)

        isPrimary = len(domains["elements"][domain_index]['clusters']) == 0

        #Get domain inventory details
        domain_details = self.domains.get_domains_details(domains_user_selection[domain_index]["id"])
        is_3x_4x_migration_env = False
        is_nsxt_cluster = False
        vc_version = None
        if domain_details and "vcenters" in domain_details and len(domain_details['vcenters']):
            vc_version = domain_details['vcenters'][0]['version']
            is_3x_4x_migration_env = int(vc_version.split(".")[0]) < 7
        if domain_details and "nsxManagers" in domain_details and domain_details["nsxManagers"]:
            is_nsxt_cluster = False
            if not is_nsxt_cluster and is_3x_4x_migration_env:
                self.utils.printRed('This operation is not supported on import of NSX-V cluster. Aborting')
                exit(1)
        else:
            is_nsxt_cluster = True

        #TODO check for secondary cluster ??
        if is_3x_4x_migration_env and not(domain_details and "domain" in domain_details and "status" in domain_details["domain"] and
                domain_details["domain"]["status"] == 'ACTIVE'):
            self.utils.printRed('Status of the domain has to be in ACTIVE status.')
            exit(1)

        #Get Unmanaged Clusters
        self.utils.printGreen("Getting unmanaged clusters info...")
        unmanagedclusterspayload = {}
        unmanagedclusterspayload["name"] = UNMANAGED_CLUSTERS_CRITERION

        clusters_response = \
            self.clusters.get_unmanaged_clusters(
                unmanagedclusterspayload,
                domains_user_selection[domain_index]["id"])
        clustersqueriesurl = 'https://' + self.hostname + clusters_response.headers['Location']

        #Poll on get unmanaged clusters queries
        clusters_query_response = self.clusters.poll_queries(clustersqueriesurl)
        clusters_user_selection = list(map(lambda x: {"name": x['name']}, clusters_query_response["elements"]))
        print(*three_line_separator, sep='\n')
        clusters_selection_text = "Please choose the cluster:"
        clusters_index = self.let_user_pick(clusters_selection_text, clusters_user_selection)
        self.utils.printGreen("Getting cluster details...")

        # Get Unmanaged Cluster
        unmanagedclusterpayload = {}
        unmanagedclusterpayload["name"] = UNMANAGED_CLUSTER_CRITERION
        cluster_response = \
            self.clusters.get_unmanaged_cluster(
                unmanagedclusterpayload,
                domains_user_selection[domain_index]["id"],
                clusters_user_selection[clusters_index]["name"])

        clusterqueryurl = 'https://' + self.hostname + cluster_response.headers['Location']

        # Poll on get unmanaged cluster queries
        cluster_query_response = self.clusters.poll_queries(clusterqueryurl)
        time.sleep(5)

        #Primary DataStore Info
        primary_datastore_info = {
            "name": cluster_query_response["elements"][0]["primaryDatastoreName"],
            "type": cluster_query_response["elements"][0]["primaryDatastoreType"]
        }
        print(*three_line_separator, sep='\n')
        self.utils.printCyan("Primary storage of the discovered cluster:")
        self.utils.printBold("Name - {}".format(primary_datastore_info['name']))
        self.utils.printBold("Type - {}".format(primary_datastore_info['type']))

        #Hosts in the unmanaged cluster
        hosts_fqdn = list(map(lambda x: {"hostName": x['fqdn'], "ipAddress": x['ipAddress'], "vmNics": x['vmNics']},
                              cluster_query_response["elements"][0]["hosts"]))
        print(*three_line_separator, sep='\n')

        self.hosts.main_func(hosts_fqdn)
        # self.utils.printCyan("Below hosts are discovered. Enter the preconfigured root passwords for all esxis :")
        # self.utils.printYellow("**Entered password is applicable for all the hosts")
        # for idx, element in enumerate(hosts_fqdn):
        #     self.utils.printBold("{}) {}".format(idx + 1, element['hostName']))
        # hosts_password = self.utils.valid_input("\033[1m Enter hosts password: \033[0m", None, None, None, True)
        # while(hosts_password != self.utils.valid_input("\033[1m Confirm password: \033[0m",
        #                                                None, None, None, True)):
        #     self.utils.printRed("Passwords don't match")
        #     hosts_password = self.utils.valid_input("\033[1m Enter hosts password: \033[0m", None, None, None, True)

        existing_dvs_specs = cluster_query_response["elements"][0]["vdsSpecs"]
        is_existing_vds = False

        existing_dvs_spec = None
        #Get the system vds if there is only one available
        #Else leave it upto Workflow Validation to verify
        if len(existing_dvs_specs) == 1:
            existing_dvs_spec = self.getSystemDvs(existing_dvs_specs, primary_datastore_info['type'])
            # Latest 4.x cluster discovery is not returning niocBandwidthAllocationSpecs in dvs spec.
            # so adding check before deleting the entry. It is not required for the domain/cluster
            # API input preparation
            if 'niocBandwidthAllocationSpecs' in existing_dvs_spec:
                del existing_dvs_spec['niocBandwidthAllocationSpecs']

        dvs_selection_text = [{"name": "Create New DVS"}, {"name" : "Use Existing DVS"} ]
        dvs_index = 0
        dvs_helper_text = ''
        print(*three_line_separator, sep='\n')

        if not is_3x_4x_migration_env:
            dvs_helper_text = "Select the DVS option to proceed"
            dvs_index = self.let_user_pick(dvs_helper_text, dvs_selection_text)

        new_dvs_spec = {}
        vmNics = []
        if dvs_index == 0:
            self.utils.printGreen("Getting compatible vmnic information...")
            # Get Unmanaged Cluster
            compatiblevmnicpayload = {}
            compatiblevmnicpayload["name"] = MATCHING_VMNIC_CRITERION
            compatible_host_response = \
                self.clusters.get_unmanaged_cluster(
                    compatiblevmnicpayload,
                    domains_user_selection[domain_index]["id"],
                    clusters_user_selection[clusters_index]["name"])
            compatiblevmnicqueries = 'https://' + self.hostname + compatible_host_response.headers['Location']

            # Poll on get compatible cluster queries
            compatible_vmnic_response = self.clusters.poll_queries(compatiblevmnicqueries)
            hosts_pnics = compatible_vmnic_response["elements"][0]["hosts"]

            if len(hosts_pnics) > 0 and  "vmNics" in hosts_pnics[0] and len(hosts_pnics[0]["vmNics"]) > 1:
                is_existing_vds = False
                print(*three_line_separator, sep='\n')
                new_vds_name = input("\033[1m Enter the New DVS name : \033[0m")

                new_dvs_spec["name"] = new_vds_name
                new_dvs_spec["isUsedByNsxt"] = True

                vmnic_maps = list(map(lambda x: {"name": x['name'], "speed": str(x['linkSpeedMB']) + 'MB',
                                                 "active": "Active" if x['isActive'] else "Inactive"},
                                      hosts_pnics[0]["vmNics"]))

                print(*three_line_separator, sep='\n')
                self.utils.printCyan("Please choose the nics for overlay traffic:")
                self.utils.printBold("-----id---speed----status")
                self.utils.printBold("-------------------------")
                for idx, element in enumerate(vmnic_maps):
                    self.utils.printBold("{}) {}-{}-{}"
                                         .format(idx + 1,
                                                 element['name'],
                                                 element['speed'],
                                                 element['active']))

                is_correct_vmnic_selection = True
                if is_3x_4x_migration_env:
                    while (is_correct_vmnic_selection):
                        try:
                            vmnic_options = list(map(int, input(
                                "\033[1m Enter your choices(only 2 numbers comma separated): \033[0m").strip().rstrip(
                                ",").split(
                                ',')))
                            while (len(vmnic_options) != 2):
                                self.utils.printRed(
                                    'VMware High Availability (HA) requires 2 vmnics. Select only 2 vmnics')
                                vmnic_options = list(map(int, input(
                                    "\033[1m Enter your choices(2 numbers comma separated): \033[0m").strip().rstrip(
                                    ",").split(
                                    ',')))
                            print(*three_line_separator, sep='\n')
                            for index,elem in enumerate(vmnic_options):
                                temp_vmnic_info = {}
                                temp_vmnic_info['id'] = vmnic_maps[elem - 1]['name']
                                temp_vmnic_info['vdsName'] = new_vds_name
                                vmNics.append(temp_vmnic_info)
                            is_correct_vmnic_selection = False
                        except:
                            print(*three_line_separator, sep='\n')
                            self.utils.print_error("\033[1m Input a number between 1(included) and {0}(included)\033[0m"
                                                .format(str(len(vmnic_maps))))
                            is_correct_vmnic_selection = True
                else:
                    while (is_correct_vmnic_selection):
                        try:
                            vmnic_options = list(map(int, input(
                                "\033[1m Enter your choices(minimum 2 numbers comma separated): \033[0m").strip().rstrip(
                                ",").split(
                                ',')))
                            while (len(vmnic_options) < 2):
                                self.utils.printRed(
                                    'VMware High Availability (HA) requires a minimum of 2 vmnics. Select minimum 2 vmnics')
                                vmnic_options = list(map(int, input(
                                    "\033[1m Enter your choices(minimum 2 numbers comma separated): \033[0m").strip().rstrip(
                                    ",").split(
                                    ',')))
                            print(*three_line_separator, sep='\n')
                            for index,elem in enumerate(vmnic_options):
                                temp_vmnic_info = {}
                                temp_vmnic_info['id'] = vmnic_maps[elem - 1]['name']
                                temp_vmnic_info['vdsName'] = new_vds_name
                                vmNics.append(temp_vmnic_info)
                            is_correct_vmnic_selection = False
                        except:
                            print(*three_line_separator, sep='\n')
                            self.utils.print_error("\033[1m Input a number between 1(included) and {0}(included)\033[0m"
                                                .format(str(len(vmnic_maps))))
                            is_correct_vmnic_selection = True
            else:
                self.utils.printRed(
                    'VMware High Availability (HA) requires a minimum of 2 vmnics. Found 0 or 1 vmnic')
                exit(1)

        elif dvs_index == 1:
            is_existing_vds = True
            dvs_names = list(map(lambda x: {"name": x['name']}, existing_dvs_specs))
            print(*three_line_separator, sep='\n')
            existing_dvs_helper = "Please select the existing dvs to continue with workload creation: "
            existing_dvs_index = self.let_user_pick(existing_dvs_helper, dvs_names)
            existing_dvs_spec = existing_dvs_specs[existing_dvs_index]
            existing_dvs_spec['isUsedByNsxt'] = True
            print(*three_line_separator, sep='\n')
            # Code to make user select PG to assign vmnics for overlay traffic
            pg_names = list(map(lambda x: {"name": x['name']}, existing_dvs_spec['portGroupSpecs']))
            existing_pg_helper = "Please select the existing portgroup to assign vmnics for overlay traffic: "
            existing_pg_index = self.let_user_pick(existing_pg_helper, pg_names)
            existing_dvs_spec['portGroupSpecs'] = [existing_dvs_spec['portGroupSpecs'][existing_pg_index]]
            # del existing_dvs_spec['niocBandwidthAllocationSpecs']
            print(*three_line_separator, sep='\n')

        nsxt_payload = self.nsxt.main_func(domains_user_selection[domain_index]["id"], isPrimary, is_3x_4x_migration_env)
        vxm_payload = self.vxrailmanager.main_func()

        self.utils.printGreen("Getting thumbprints for Hosts and VxRail Manager...")
        print(*three_line_separator, sep='\n')
        vxrm_fqdn = self.populatevxrmfqdn(domains_user_selection[domain_index]["id"],
                                          clusters_user_selection[clusters_index]["name"])
        fqdn_to_thumbprint_dict = self.hosts.get_ssh_thumbprints(hosts_fqdn, domains_user_selection[domain_index]["id"],
                                                                 vxrm_fqdn, vxm_payload['adminCredentials']['username'],
                                                                 vxm_payload['adminCredentials']['password'])
        # Updating SSH Thumbprint to VxRail Manager payload
        vxm_payload['sshThumbprint'] = fqdn_to_thumbprint_dict.get(vxrm_fqdn)

        print(*three_line_separator, sep='\n')
        ignoreVsanLicense = primary_datastore_info['type'] != 'VSAN'
        licenses_payload = self.licenses.main_func(ignoreVsanLicense)

        cluster_payload = {}
        if isPrimary:
            cluster_payload['clusterSpec'] = {}
            cluster_payload['clusterSpec']['name'] = clusters_user_selection[clusters_index]["name"]
            cluster_payload['clusterSpec']['skipThumbprintValidation'] = False
            cluster_payload['clusterSpec']['vxRailDetails'] = vxm_payload
            cluster_payload['clusterSpec']['datastoreSpec'] = {
                "vsanDatastoreSpec": {
                    "datastoreName": primary_datastore_info['name'],
                    "licenseKey": licenses_payload['licenseKeys']['VSAN']
                } if primary_datastore_info['type'] == 'VSAN' else None,
                "vmfsDatastoreSpec": {
                    "fcSpec": [
                        {
                            "datastoreName": primary_datastore_info['name']
                        }
                    ]
                } if primary_datastore_info['type'] == 'FC' else None
            }
            cluster_payload['clusterSpec']['networkSpec'] = self.populatenetworkSpec(
                is_existing_vds, existing_dvs_spec, new_dvs_spec, nsxt_payload, isPrimary)
            cluster_payload['clusterSpec']['hostSpecs'] = self.hosts.populatehostSpec(is_existing_vds, hosts_fqdn,
                                                                                      vmNics, fqdn_to_thumbprint_dict)
            cluster_payload['nsxTSpec'] = self.populatensxtSpec(
                nsxt_payload, licenses_payload)

            cluster_payload_copy = copy.deepcopy(cluster_payload)
            self.maskPasswords(cluster_payload_copy)
            print(json.dumps(cluster_payload_copy, indent=2, sort_keys=True))
            input("\033[1m Enter to continue ...\033[0m")
            self.domains.update_workload_domain(cluster_payload, domains_user_selection[domain_index]["id"])

        else:
            cluster_payload['computeSpec'] = {}
            cluster_payload['computeSpec']['clusterSpecs'] = [{}]
            # cluster_payload['computeSpec']['clusterSpecs'].append({})
            cluster_payload['computeSpec']['clusterSpecs'][0]['datastoreSpec'] = {
                "vsanDatastoreSpec": {
                    "datastoreName": primary_datastore_info['name'],
                    "licenseKey": licenses_payload['licenseKeys']['VSAN']
                } if primary_datastore_info['type'] == 'VSAN' else None,
                "vmfsDatastoreSpec": {
                    "fcSpec": [
                        {
                            "datastoreName": primary_datastore_info['name']
                        }
                    ]
                } if primary_datastore_info['type'] == 'FC' else None
            }
            cluster_payload['computeSpec']['clusterSpecs'][0]['skipThumbprintValidation'] = False
            cluster_payload['computeSpec']['clusterSpecs'][0]['name'] = clusters_user_selection[clusters_index]["name"]
            cluster_payload['computeSpec']['clusterSpecs'][0]['networkSpec'] = self.populatenetworkSpec(
                is_existing_vds, existing_dvs_spec, new_dvs_spec, nsxt_payload, isPrimary)
            cluster_payload['computeSpec']['clusterSpecs'][0]['vxRailDetails'] = vxm_payload

            cluster_payload['computeSpec']['clusterSpecs'][0]['hostSpecs'] = self.hosts.populatehostSpec(
                is_existing_vds, hosts_fqdn, vmNics, fqdn_to_thumbprint_dict)
            cluster_payload['domainId'] = domains_user_selection[domain_index]["id"]

            cluster_payload_copy = copy.deepcopy(cluster_payload)
            self.maskPasswords(cluster_payload_copy)
            print (json.dumps(cluster_payload_copy, indent=2, sort_keys=True))
            input("\033[1m Enter to continue ...\033[0m")
            self.clusters.create_cluster(cluster_payload)

        exit(1)

if __name__ == "__main__":
    VxRaiWorkloadAutomator().initApp()
