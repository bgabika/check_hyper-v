#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------
# COREX Microsoft Hyper-V check plugin for Icinga 2
# Copyright (C) 2019-2022, Gabor Borsos <bg@corex.bg>
# 
# v1.1 built on 2022.12.13.
# usage: check_hyper-v.py --help
#
# For bugs and feature requests mailto bg@corex.bg
# 
# ---------------------------------------------------------------
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# Test it in test environment to stay safe and sensible before 
# using in production!
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# ---------------------------------------------------------------

import io
import sys

try:
    from enum import Enum
    import argparse
    import paramiko
    import re
    import textwrap

except ImportError as e:
    print("Missing python module: {}".format(str(e)))
    sys.exit(255)


class CheckState(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3


class CheckHyperV:

    def __init__(self):

        self.pluginname = "check_hyper-v.py"
        self.result_list = []
        self.parse_args()


    def parse_args(self):
        parser = argparse.ArgumentParser(
            prog=self.pluginname, 
            add_help=True, 
            formatter_class=argparse.RawTextHelpFormatter,
            description = textwrap.dedent("""
            PLUGIN DESCRIPTION: COREX Microsoft Hyper-V check plugin for Icinga 2."""),
            epilog = textwrap.dedent(f"""
            Examples:
            {self.pluginname} --hostname myserver.mydomain.com --sshuser john.doe --sshkey mykey --memwarning 20 --memcritical 30 --cpuwarning 60 --cpucritical 80"""))
            
        ssh_connect_opt = parser.add_argument_group('SSH connection arguments', 'hostname, sshuser, sshport, sshkey')

        ssh_connect_opt.add_argument('--hostname', dest="hostname", type=str, required=True, help="host FQDN or IP")
        ssh_connect_opt.add_argument('--sshport', type=int, required=False, help="ssh port, default port: 22", default=22)
        ssh_connect_opt.add_argument('--sshuser', type=str, required=True, help="ssh user")
        ssh_connect_opt.add_argument('--sshkey', type=str, required=True, help="ssh key file")


        check_procedure_opt = parser.add_argument_group('VM performance arguments', 'ignore-vm, memwarning, memcritical, cpuwarning, cpucritical')
        
        check_procedure_opt.add_argument('--ignore-vm', dest='ignore_vm', action='append', metavar='VM-NAME',
                                        help='Ignore VM from checking, --ignore-vm "vm-name1" --ignore-vm "vm-name1" ...etc', default=[])

        check_procedure_opt.add_argument('--memwarning', dest='threshold_memwarning', type=int, required=True,
                                        help='Percent warning threshold for VM memory usage.')
        
        check_procedure_opt.add_argument('--memcritical', dest='threshold_memcritical', type=int, required=True,
                                        help='Percent critical threshold for VM memory usage.')

        check_procedure_opt.add_argument('--cpuwarning', dest='threshold_cpuwarning', type=int, required=True,
                                        help='Percent warning threshold for VM CPU usage.')
        
        check_procedure_opt.add_argument('--cpucritical', dest='threshold_cpucritical', type=int, required=True,
                                        help='Percent warning threshold for VM CPU usage.')

        self.options = parser.parse_args()

        # check thresholds scale
        if self.check_thresholds_scale(self.options.threshold_memwarning, self.options.threshold_memcritical) == False:
            parser.error(f"--memwarning threshold must be lower then --memcritical threshold!")
        if self.check_thresholds_scale(self.options.threshold_cpuwarning, self.options.threshold_cpucritical) == False:
            parser.error(f"--cpuwarning threshold must be lower then --cpucritical threshold!")



    def main(self):
        
        self.get_windows_services(self.options.hostname, self.options.sshport, self.options.sshuser, self.options.sshkey)
        self.get_windows_feature(self.options.hostname, self.options.sshport, self.options.sshuser, self.options.sshkey)
        self.get_wm_state(self.options.hostname, self.options.sshport, self.options.sshuser, self.options.sshkey)
        self.check_exitcodes(self.result_list)
    


    @staticmethod
    def output(state, message):
        prefix = state.name
        message = '{} - {}'.format(prefix, message)

        print(message)
        sys.exit(state.value)



    @staticmethod
    def check_UOM(mynumber):
        mynumber_lenght = len(str(mynumber))
        my_unit = "GB"
        if mynumber_lenght >= 13:
            mynumber = round(mynumber/1024**4, 2)
            my_unit = "TB"
            
        if mynumber_lenght >= 10 and mynumber_lenght <= 12:
            mynumber = round(mynumber/1024**3, 2)
            my_unit = "GB"

        if mynumber_lenght < 10:
            mynumber = round(mynumber/1024**2, 2)
            my_unit = "MB"

        return mynumber, my_unit



    @staticmethod
    def check_ssh(hostname, port, username, keyfile):
        keyfile = paramiko.RSAKey.from_private_key_file(keyfile)
        ssh = paramiko.SSHClient()
        
        try:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, port, username, pkey=keyfile, allow_agent=False, look_for_keys=False, timeout=30, banner_timeout=30, auth_timeout=30)
            status = 0
            ssh.close()
            return status
        except:
            print(f"\tCould not connect to {hostname}!")
            sys.exit(1)
            

    @staticmethod
    def clean_string(mystring):
        return re.sub('\s+',' ',mystring)


    @staticmethod
    def check_thresholds_scale(threshold_warning, threshold_critical):
        return(threshold_warning < threshold_critical)
               
        

    def run_ssh_command(self, command, hostname, sshport, sshuser, keyfile, email_rcpt=""):
        ssh_status = self.check_ssh(hostname, sshport, sshuser, keyfile)
        keyfile = paramiko.RSAKey.from_private_key_file(keyfile)
        if ssh_status == 0:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, port=sshport, username=sshuser, pkey=keyfile, allow_agent=False, look_for_keys=False, timeout=30, banner_timeout=30, auth_timeout=30)
            stdin, stdout, stderr = ssh.exec_command(command)
            stdin.flush()

            stdout = io.TextIOWrapper(stdout, encoding='utf-8', errors='replace')
            output = (''.join(stdout.readlines()))
        else:
            self.output(CheckState.WARNING, f"Cannot run remote command ({command}) on {hostname}, please check ssh connection!")
            
        return output



    def get_windows_services(self, hostname, sshport, sshuser, sshkey):
        
        perfdata_dict = {}
        wincommand = """powershell "Get-CimInstance win32_service -filter \\"name='vmms'\\"| Select Name,Displayname,StartMode,State,Startname,Status\""""
        perfdata = self.run_ssh_command(wincommand, hostname, sshport, sshuser, sshkey)
        
        perfdata_list = perfdata.splitlines()
        perfdata_list = list(filter(None, perfdata_list))

        for element in perfdata_list:
            element_list = element.split(":")
            perfdata_dict[element_list[0].strip()] = element_list[1].strip()


        if perfdata_dict["State"] != "Running":
            self.result_list.append(f"CRITICAL - Windows {perfdata_dict['Name']} service state is {perfdata_dict['State']}!")
        else:
            self.result_list.append(f"OK - Windows {perfdata_dict['Name']} service state is {perfdata_dict['State']}.")



    def get_windows_feature(self, hostname, sshport, sshuser, sshkey):
        
        perfdata_dict = {}
        wincommand = """powershell "Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V\""""

        perfdata = self.run_ssh_command(wincommand, hostname, sshport, sshuser, sshkey)
        perfdata = (perfdata.strip()).replace(",", ".")
        perfdata_list = perfdata.splitlines()
        perfdata_list = [x for x in perfdata_list if "FeatureName" in x or "State" in x]

        for element in perfdata_list:
            element_list = element.split(":")
            perfdata_dict[element_list[0].strip()] = element_list[1].strip()


        if perfdata_dict["State"] != "Enabled":
            self.result_list.append(f"CRITICAL - {perfdata_dict['FeatureName']} feature state is {perfdata_dict['State']}!")
        else:
            self.result_list.append(f"OK - {perfdata_dict['FeatureName']} feature state is {perfdata_dict['State']}.")


    
    def get_wm_state(self, hostname, sshport, sshuser, sshkey):
        all_vms_perfdata_list = []
        vm_perfdata_dictionary_list = []

        wincommand = """powershell "$vmname = (Get-VM | select name | ft -HideTableHeaders -autosize) | Out-String; $linearray = $vmname.Split(\\"`n\\"); foreach ($i in $linearray) {if ($i.Length -gt 1){get-vm $i.trim() | select Name, State, CPUUsage, MemoryAssigned, MemoryDemand, Uptime, Status, Version;Get-VM $i.trim() | Select-Object -ExpandProperty NetworkAdapters | Select-Object SwitchName}}\""""
        perfdata = self.run_ssh_command(wincommand, hostname, sshport, sshuser, sshkey)
        perfdata_list = perfdata.splitlines()
        perfdata_list = list(filter(None, perfdata_list))

        name_index_number = ([perfdata_list.index(x) for x in perfdata_list if "Name" in x and "SwitchName" not in x])
        
        for number in name_index_number:
            try:
                vm_perfdata_endline = name_index_number.index(number)+1
                vm_perfdata_endline = ((name_index_number[vm_perfdata_endline]))
            except:
                vm_perfdata_endline = name_index_number.index(number)
                vm_perfdata_endline = (name_index_number[vm_perfdata_endline])+9

            all_vms_perfdata_list.append(perfdata_list[number:vm_perfdata_endline])

        
        for vm_perfdata_list in all_vms_perfdata_list:
            perfdata_dict = {}
            for vm_perfdata in vm_perfdata_list:
                vm_perfdata_for_dict = (vm_perfdata.split(":", 1))
                perfdata_dict[(vm_perfdata_for_dict[0]).strip()] = (vm_perfdata_for_dict[1]).strip()
            
            vm_perfdata_dictionary_list.append(perfdata_dict)
        
        
        for vm_perfdata_element in vm_perfdata_dictionary_list:
            vm_name = vm_perfdata_element['Name']
            try:
                vm_memory_percent_usage = round(((int(vm_perfdata_element["MemoryDemand"]) / int(vm_perfdata_element["MemoryAssigned"])))*100, 2)
            except:
                vm_memory_percent_usage = 0
            
            vm_cpu_percent_usage = float(vm_perfdata_element['CPUUsage'])
            vm_memory_full, UOM_full = self.check_UOM(int(vm_perfdata_element["MemoryAssigned"]))
            vm_memory_usage, UOM_usage = self.check_UOM(int(vm_perfdata_element["MemoryDemand"]))
            
            uptime =  vm_perfdata_element['Uptime'].split(":")
            uptime = f"{uptime[0]}:{uptime[1]}:{(int(round(float(uptime[2]),2))):02d}"
            switchname = vm_perfdata_element['SwitchName']
            if len(switchname) < 1:
                switchname = "None"

            vm_details = self.clean_string(f"'{vm_name}' VM state is {vm_perfdata_element['State']}, \
                        CPU usage: {vm_cpu_percent_usage}%, \
                        memory usage: {vm_memory_percent_usage}% ({vm_memory_usage} {UOM_usage} / {vm_memory_full} {UOM_full}), \
                        switch name: {switchname},\
                        VM health: {vm_perfdata_element['Status']},\
                        uptime: {uptime}\
                        |{vm_name} memory={vm_memory_percent_usage}%;{self.options.threshold_memwarning};{self.options.threshold_memcritical};0;100\
                          {vm_name} cpu={vm_cpu_percent_usage}%;{self.options.threshold_cpuwarning};{self.options.threshold_cpucritical};0;100")

            
            if vm_perfdata_element['Name'] not in self.options.ignore_vm:
                if vm_perfdata_element["State"] == "Off":
                    self.result_list.append(f"WARNING - {vm_details}")
                else:
                    if vm_perfdata_element['Status'] != 'Operating normally':
                        self.result_list.append(f"CRITICAL - {vm_details}")
                    else:
                        if vm_memory_percent_usage >= self.options.threshold_memcritical:
                            self.result_list.append(f"CRITICAL - Memory usage: {vm_details}")
                        elif self.options.threshold_memcritical > vm_memory_percent_usage and vm_memory_percent_usage >= self.options.threshold_memwarning:
                            self.result_list.append(f"WARNING - Memory usage: {vm_details}")
                        else:
                            if vm_cpu_percent_usage >= self.options.threshold_cpucritical:
                                self.result_list.append(f"CRITICAL - CPU usage: {vm_details}")
                            elif self.options.threshold_cpucritical > vm_cpu_percent_usage and vm_cpu_percent_usage >= self.options.threshold_cpuwarning:
                                self.result_list.append(f"WARNING - CPU usage: {vm_details}")
                            else:
                                if switchname == "None":
                                    self.result_list.append(f"CRITICAL - No vSwitch connection: {vm_details}")
                                else:
                                    self.result_list.append(f"OK - {vm_details}")
            else:
                self.result_list.append(f"OK - IGNORED VM: {vm_details}")
                


    def check_exitcodes(self, result_list):

        if any("CRITICAL" in x for x in result_list):
            [print(x) for x in result_list if re.search("CRITICAL", x)]
        if any("WARNING" in x for x in result_list):
            [print(x) for x in result_list if re.search("WARNING", x)]
        if any("OK -" in x for x in result_list):
            [print(x) for x in result_list if re.search("OK -", x)]
        
    
        if any("CRITICAL" in x for x in result_list):
            sys.exit(2)
        if any("WARNING" in x for x in result_list):
            sys.exit(1)
        
        sys.exit(0)
        


check_win = CheckHyperV()
check_win.main()
