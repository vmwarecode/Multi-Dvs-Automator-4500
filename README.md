# Multi Dvs Automation Script

## Table of contents
- [Quick start](#quick-start)

## Quick start

Unzip the file and copy the directory MultiDvsAutomator to /home/vcf/ directory on the SDDC Manager VM.


> Please note that you are running the script in sddc-manager VM.
> Forward and reverse DNS settings for nsxt and esxi components should be preconfigured.
> Workload Domain must be provisioned.
> Host configuration must have minimum two active vmNics.
> A DHCP server must be configured for NSX-T VTEPS.



## Usage

```python
root@sddc-manager [ /home/vcf/MultiDvsAutomator ]# python3 vxrailworkloadautomator.py
 Enter the SSO username: administrator@vsphere.local
 Enter the SSO password:
 Welcome to VxRail Workload Automator
 Initializing Domains Automator
 Initializing Clusters Automator
 Getting the domains..



 Please choose the domain to which cluster has to be imported:
 1) sddcId-1010
 2) vi-vxrail
 Enter your choice(number): 2
 Getting unmanaged clusters info...



 Please choose the cluster:
 1) VxRail-Virtual-SAN-Cluster-WLD
 Enter your choice(number): 1
 Getting cluster details...



 Below hosts are discovered. Enter the password for them:
 1) esxi-5.vrack.vsphere.local
 2) esxi-6.vrack.vsphere.local
 3) esxi-7.vrack.vsphere.local



 Please choose password option:
 1) Input one password that is applicable to all the hosts (default)
 2) Input password individually for each host
 Enter your choice(number): 2



 Input root password of host esxi-8.vrack.vsphere.local
 Enter root password:
 Confirm password:



 Input root password of host esxi-9.vrack.vsphere.local
 Enter root password:
 Confirm password:



 Input root password of host esxi-10.vrack.vsphere.local
 Enter root password:
 Confirm password:


 Existing dvs for the discovered cluster:
 1) SDDC-Dswitch-Private-WLD



 Select the DVS option to proceed
 1) Create New DVS
 2) Use Existing DVS
 Enter your choice(number): 1
 Getting compatible vmnic information...



 Enter the New DVS name : test-vds



 Please choose the nics for overlay traffic:
 -----id---speed----status
 -------------------------
 1) vmnic2-10000MB-Active
 2) vmnic3-10000MB-Active
 Enter your choices(minimum 2 numbers comma separated): 1,2



 Getting shared NSX-T cluster information...
 ** No shared NSX-T instance was found, you need to create a new one



 Enter Geneve vLAN ID (0-4096): 0
 Enter Admin password:
 Confirm Admin password:



 Please Enter NSX-T VIP details
 FQDN (IP address will be fetched from DNS): nsxt-manager.vrack.vsphere.local
 Resolving IP from DNS...
 Resolved IP address: 10.0.0.151
 Gateway IP address: 10.0.0.250
 Subnet mask (255.255.255.0):



 Enter FQDN for 1st NSX-T Manager: nsxt-manager-1.vrack.vsphere.local
 Resolving IP from DNS...
 Resolved IP address: 10.0.0.193



 Enter FQDN for 2nd NSX-T Manager: nsxt-manager-2.vrack.vsphere.local
 Resolving IP from DNS...
 Resolved IP address: 10.0.0.194



 Enter FQDN for 3rd NSX-T Manager: nsxt-manager-3.vrack.vsphere.local
 Resolving IP from DNS...
 Resolved IP address: 10.0.0.195



 Please input VxRail Manager root credential
 Enter password:
 Confirm password:



 Please input VxRail Manager admin credential
 Enter username (mystic):
 Enter password:
 Confirm password:



 Getting license information...
 Please choose a VSAN license:
 1)--vsanLicense--
 Enter your choice(number): 1



 Please choose a NSX-T license:
 1) --nsxTLicense--
 Enter your choice(number): 1


 {
  "clusterSpec": {
    "datastoreSpec": {
      "vsanDatastoreSpec": {
        "licenseKey": "--vsanLicense--"
      }
    },
    "hostSpecs": [
      {
        "hostName": "esxi-5.vrack.vsphere.local",
        "hostNetworkSpec": {
          "vmNics": [
            {
              "id": "vmnic2",
              "vdsName": "test-vds"
            },
            {
              "id": "vmnic3",
              "vdsName": "test-vds"
            }
          ]
        },
        "ipAddress": "10.0.0.104",
        "password": "*******",
        "username": "root"
      },
      {
        "hostName": "esxi-6.vrack.vsphere.local",
        "hostNetworkSpec": {
          "vmNics": [
            {
              "id": "vmnic2",
              "vdsName": "test-vds"
            },
            {
              "id": "vmnic3",
              "vdsName": "test-vds"
            }
          ]
        },
        "ipAddress": "10.0.0.105",
        "password": "*******",
        "username": "root"
      },
      {
        "hostName": "esxi-7.vrack.vsphere.local",
        "hostNetworkSpec": {
          "vmNics": [
            {
              "id": "vmnic2",
              "vdsName": "test-vds"
            },
            {
              "id": "vmnic3",
              "vdsName": "test-vds"
            }
          ]
        },
        "ipAddress": "10.0.0.106",
        "password": "*******",
        "username": "root"
      }
    ],
    "name": "VxRail-Virtual-SAN-Cluster-WLD",
    "networkSpec": {
      "nsxClusterSpec": {
        "nsxTClusterSpec": {
          "geneveVlanId": 0
        }
      },
      "vdsSpecs": [
        {
          "isUsedByNsxt": true,
          "name": "test-vds"
        }
      ]
    },
    "vxRailDetails": {
      "adminCredentials": {
        "credentialType": "SSH",
        "password": "*******",
        "username": "mystic"
      },
      "rootCredentials": {
        "credentialType": "SSH",
        "password": "*******",
        "username": "root"
      }
    }
  },
  "nsxTSpec": {
    "licenseKey": "--nsxTLicense--",
    "nsxManagerAdminPassword": "*******",
    "nsxManagerSpecs": [
      {
        "name": "nsxt-manager-1",
        "networkDetailsSpec": {
          "dnsName": "nsxt-manager-1.vrack.vsphere.local",
          "gateway": "10.0.0.250",
          "ipAddress": "10.0.0.193",
          "subnetMask": "255.255.255.0"
        }
      },
      {
        "name": "nsxt-manager-2",
        "networkDetailsSpec": {
          "dnsName": "nsxt-manager-2.vrack.vsphere.local",
          "gateway": "10.0.0.250",
          "ipAddress": "10.0.0.194",
          "subnetMask": "255.255.255.0"
        }
      },
      {
        "name": "nsxt-manager-3",
        "networkDetailsSpec": {
          "dnsName": "nsxt-manager-3.vrack.vsphere.local",
          "gateway": "10.0.0.250",
          "ipAddress": "10.0.0.195",
          "subnetMask": "255.255.255.0"
        }
      }
    ],
    "vip": "10.0.0.151",
    "vipFqdn": "nsxt-manager.vrack.vsphere.local"
  }
}


 Enter to continue ...
 Validating the input....
 Validation started for import cluster operation. The validation id is: c7799067-2bed-44f8-9ac2-6f8724240bbe
 Polling on validation api https://localhost/v1/domains/validations/c7799067-2bed-44f8-9ac2-6f8724240bbe
 Validate import domain operation ended with status: SUCCEEDED
 Enter to import cluster..
 Importing cluster, monitor the status of the task(task-id: c7799067) from sddc-manager ui
```



## Thanks

