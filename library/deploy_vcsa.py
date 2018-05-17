#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2015 VMware, Inc. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
# to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
# TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

__author__ = 'yfauser'

import requests
import ssl

from pyVim.connect import SmartConnect
from pyVmomi import vim, vmodl


def find_virtual_machine(content, searched_vm_name):
    virtual_machines = get_all_objs(content, [vim.VirtualMachine])
    for vm in virtual_machines:
        if vm.name == searched_vm_name:
            return vm
    return None


def get_all_objs(content, vimtype):
    obj = {}
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for managed_object_ref in container.view:
        obj.update({managed_object_ref: managed_object_ref.name})
    return obj


def connect_to_api(vchost, vc_user, vc_pwd):
    try:
        service_instance = SmartConnect(host=vchost, user=vc_user, pwd=vc_pwd)
    except (requests.ConnectionError, ssl.SSLError):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            service_instance = SmartConnect(host=vchost, user=vc_user, pwd=vc_pwd, sslContext=context)
        except Exception as e:
            raise Exception(e)
    return service_instance.RetrieveContent()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path_to_ova=dict(required=True, type='str'),
            ova_file=dict(required=True, type='str'),
            vcsa_deploy=dict(required=True, type='str'),
            vcenter=dict(required=True, type='str'),
            vcenter_user=dict(required=True, type='str'),
            vcenter_passwd=dict(required=True, type='str', no_log=True),
            portgroup=dict(required=True, type='str'),
            datastore=dict(required=True, type='str'),
            datacenter=dict(required=True, type='str'),
            cluster=dict(required=True, type='str'),
            vmname=dict(required=True, type='str'),
            ip_address=dict(required=True, type='str'),
            dns_server=dict(required=True, type='str'),
            prefix=dict(type='str'),
            gateway=dict(required=True, type='str'),
            admin_password=dict(required=True, type='str', no_log=True),
            ntp_server=dict(required=True, type='str'),
            dns_domain=dict(required=True, type='str'),
            site=dict(required=True, type='str')
        ),
        supports_check_mode=True,
    )

    try:
        content = connect_to_api(module.params['vcenter'], module.params['vcenter_user'],
                                 module.params['vcenter_passwd'])
        
    except vim.fault.InvalidLogin:
        module.fail_json(msg='exception while connecting to vCenter, login failure, check username and password')
    except requests.exceptions.ConnectionError:
        module.fail_json(msg='exception while connecting to vCenter, check hostname, FQDN or IP')

    nsx_manager_vm = find_virtual_machine(content, module.params['vmname'])

    if nsx_manager_vm:
        module.exit_json(changed=False, msg='A VM with the name {} was already present'.format(module.params['vmname']))

#    vcsa_deploy_command = [module.params['ovftool_path']]


    j  = '{\n'
    j += '    "__version": "2.13.0",\n'
    j += '    "new_vcsa": {\n'
    j += '        "vc": {\n'
    j += '            "hostname": "{}",\n'.format(module.params['vcenter'])
    j += '            "username": "{}",\n'.format(module.params['vcenter_user'])
    j += '            "password": "{}",\n'.format(module.params['vcenter_passwd'])
    j += '            "deployment_network": "{}",\n'.format(module.params['portgroup'])
    j += '            "datastore": "{}",\n'.format(module.params['datastore'])
    j += '            "datacenter": "{}",\n'.format(module.params['datacenter'])
    j += '            "target": [ "{}" ]\n'.format(module.params['cluster'])
    j += '        },\n'
    j += '        "appliance": {\n'
    j += '            "thin_disk_mode": true,\n'
    j += '            "deployment_option": "small",\n'
    j += '            "name": "{}"\n'.format(module.params['vmname'])
    j += '        },\n'
    j += '        "network": {\n'
    j += '            "ip_family": "ipv4",\n'
    j += '            "mode": "static",\n'
    j += '            "ip" : "{}",\n'.format(module.params['ip_address'])                     
    j += '            "dns_servers": [\n'
    j += '                "{}"\n'.format(module.params['dns_server'])
    j += '            ],\n'
    j += '            "prefix": "{}",\n'.format(module.params['prefix'])
    j += '            "gateway": "{}",\n'.format(module.params['gateway'])
    j += '            "system_name": "{}"\n'.format(module.params['ip_address'])
    j += '        },\n'
    j += '        "os": {\n'
    j += '            "password": "{}",\n'.format(module.params['admin_password'])
    j += '            "ntp_servers": "{}",\n'.format(module.params['ntp_server'])
    j += '            "ssh_enable": true\n'
    j += '        },\n'
    j += '        "sso": {\n'
    j += '            "password": "{}",\n'.format(module.params['admin_password'])
    j += '            "domain_name": "{}"\n'.format(module.params['dns_domain'])
    j += '        }\n'
    j += '    },\n'
    j += '    "ceip": {\n'
    j += '        "settings": {\n'
    j += '            "ceip_enabled": true\n'
    j += '        }\n'
    j += '    }\n'
    j += '}\n'

    filename="/home/ftallet/nsxt-ansible/vcsa.json"
    file = open(filename,"w")
    file.write(j)
    file.close
    
    deploy_command = [ module.params['vcsa_deploy'] , 'install', '--no-ssl-certificate-verification',
                       '--accept-eula', '--acknowledge-ceip', '/home/ftallet/nsxt-ansible/vcsa.json' ]

    deploy_result = module.run_command(deploy_command)
    if deploy_result[0] != 0:
        module.fail_json(msg='Failed to deploy VCSA, error message from vcsa-deploy is: {}, the command was {}'.format(deploy_result[1], deploy_command))

    
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
