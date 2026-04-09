#!/usr/bin/env python3

"""
This program is developed by Truong Le (truole@cisco.com) for network information collection or interactive login.
Multiple jump hosts, telnet & ssh, Cisco, Juniper, Nokia, Huawei routers are supported.
It requires the pexpect module thus only Mac-OS and Linux/Unix are supported.
User can interactively input the names of login configuration file, device seed file, and command base directory,
or they can be predefined in the yaml NetCollect config files put in the same directory of this program.
Example of NetCollect config:
- name: "Cisco BU vLab"
  login_config_file: "/Users/truole/BU_Lab/login_config.yml"
  device_seed_file: "/Users/truole/BU_Lab/all_device.csv"
  cmd_base_dir: "/Users/truole/BU_Lab/cmd"
"""

import os
import sys
import threading
import time
import datetime
import pexpect
from pytz import timezone, all_timezones
from ruamel import yaml
from glob import glob


# ----------------------------------------------------------------------------------------------------------------------
def parse_login_config(config_file_name):
    
    """
    This function parses and validates the yaml login configuration file.
    jump section is optional, multiple hosts are supported. device section is mandatory as device default config.
    Device-specific parameters can also be defined in the device seed file.

    jump:
     - name: 'jump-server-1'           optional
       address: '1.1.1.1'              mandatory
       protocol: ''                    optional, default 'ssh' if 'telnet' not set
       port: '100'                     optional, default '22' for ssh, '23' for telnet
       username: 'ubuntu'              mandatory
       userident: '~/.ssh/identity'    optional
       userpass: ''                    optional
       cmd: '/usr/bin/ssh'             optional, default is protocol
       prompt: '@.*\]\$'               mandatory, regexp, must be in single quote

    device:
     username: 'device_user'           mandatory
     userpass: 'device_pass'           mandatory
     protocol: ''                      optional, default 'ssh' if 'telnet' not set
     cmd: ''                           optional, default is protocol
     prompt: '\n.*#'				   optional, default is Cisco prompt (\n.*#)

    """

    default_prompt = r'\n.*#'

    with open(config_file_name, 'r') as login_config_file:
        login_config_dict = yaml.safe_load(login_config_file)

    # Extract configuration of jump host if any
    config_list = login_config_dict.get("jump")

    if config_list:
        # check if any duplicate of jump hosts address
        address_list = [host["address"] for host in config_list]
        if len(set(address_list)) != len(address_list):
            return "failed_duplicate_jump_address", None

        for config_index, config_dict in enumerate(config_list):
            # check if enough mandatory information for each jump host
            if not all(config_dict.get(item) for item in ["address", "username", "prompt"]):
                return "failed_invalid_jump_config", None

            else:
                config_dict["name"] = config_dict.get("name") or "jump-{0}".format(str(config_index))
                config_dict["protocol"] = "telnet" if (config_dict.get("protocol")
                                                       and config_dict["protocol"].lower() == "telnet") else "ssh"
                config_dict["port"] = config_dict.get("port") or ("23" if config_dict["protocol"] == "telnet" else "22")
                config_dict["cmd"] = config_dict.get("cmd") or config_dict["protocol"]

    # Extract device configuration
    config_dict = login_config_dict.get("device")

    if not config_dict or not all(config_dict.get(item) for item in ["username", "userpass"]):
        return "failed_invalid_device_config", None

    else:
        config_dict["protocol"] = "telnet" if (config_dict.get("protocol")
                                               and config_dict["protocol"].lower() == "telnet") else "ssh"
        config_dict["port"] = config_dict.get("port") or ("23" if config_dict["protocol"] == "telnet" else "22")
        config_dict["cmd"] = config_dict.get("cmd") or config_dict["protocol"]
        config_dict["prompt"] = config_dict.get("prompt") or default_prompt

    return "done", login_config_dict


# ----------------------------------------------------------------------------------------------------------------------
def parse_seed_file(cmd_dir_name, seed_file_name, net_collect_mode):
    
    """
    This function parses and validates information from the csv device seed file.
    A device entry is valid only if its length is 13 column minimum as:
    address,command-file,ping-file,name,protocol,port,vendor,prompt,username,userpass,login-cmd,platform,software.
    It's not necessary to pop information for all columns. Only 'ssh' and 'telnet' are valid for the protocol.
    Port is "23" for telnet or "22" for ssh if not specified. Vendor can be in ["cisco", "huawei", "juniper", "nokia"].
    Prompt is derived from vendor if not specified.
    """

    cisco_prompt = r'\n.*#'
    nokia_prompt = r'\n.*#'
    juniper_prompt = r'@.*\>'
    huawei_prompt = r'\<.*\>'

    vendor_dict = {"cisco": cisco_prompt, "nokia": nokia_prompt, "huawei": huawei_prompt, "juniper": juniper_prompt}
    min_col_quantity = 13
    file_dict = {}
    result_msg = ""
    result_dict = {}

    with open(seed_file_name, 'r') as seed_file:
        seed_lines = seed_file.readlines()

    seed_lines = [[col.strip() for col in line.rstrip('\r\n ').split(',')]
                  for line in seed_lines if not line.startswith('#') and not line.rstrip('\r\n ') == '']

    # Validate if the .csv seed file has enough quantity of columns
    col_quantity = min(len(line) for line in seed_lines)
    if col_quantity < min_col_quantity:
        result_msg = "Unexpected length of device entries in the seed file."
        return result_msg, result_dict

    # Validate files existence and extract information from them
    if net_collect_mode == "1":
        cmd_files = list(set([line[1] for line in seed_lines if line[1] != ""]))
        ping_files = list(set([line[2] for line in seed_lines if line[2] != ""]))
        all_files = cmd_files + ping_files

        if all_files:
            for file_name in all_files:
                file_full_name = os.path.join(cmd_dir_name, file_name)
                if not os.path.isfile(file_full_name):
                    result_msg = "The file '{0}' in seed file does not exist.".format(file_name)
                    file_dict = {}
                    break

                else:
                    with open(file_full_name, "r") as in_file:
                        in_list = [line.strip('\r\n ') for line in in_file.readlines() if not line.startswith(r"#")]
                    file_dict[file_name] = in_list

            if not file_dict:
                return result_msg, result_dict

            # Further data process for ping file
            for file_name in ping_files:
                line_list = file_dict[file_name]
                line_list = [line.split(",") for line in line_list]
                file_dict[file_name] = line_list

    # extract information for each device
    for line in seed_lines:
        if net_collect_mode == "1":
            cmd_list = file_dict[line[1]] if line[1] != "" else []
            ping_list = file_dict[line[2]] if line[2] != "" else []
        else:
            cmd_list = ping_list = []

        address, name, vendor = line[0], line[3] or line[0], line[6].lower()
        platform, software, login_dict = line[11], line[12], {"address": address, "name": name}
        device_unique = line[0] + "_" + line[5] if line[5] else line[0]

        if line[4].lower() in ["telnet", "ssh"]:
            login_dict["protocol"] = line[4].lower()

        if line[5].isdigit():
            login_dict["port"] = line[5]

        if line[7]:
            login_dict["prompt"] = line[7]
        elif vendor in vendor_dict:
            login_dict["prompt"] = vendor_dict[vendor]

        if line[8]:
            login_dict["username"] = line[8]

        if line[9]:
            login_dict["userpass"] = line[9]

        if line[10]:
            login_dict["cmd"] = line[10]
        elif login_dict.get("protocol"):
            login_dict["cmd"] = login_dict["protocol"]

        result_dict[device_unique] = {"address": address, "name": name, "vendor": vendor, "platform": platform,
                                      "software": software, "exec": cmd_list, "ping": ping_list, "login": login_dict}

    result_msg = "done"
    return result_msg, result_dict


# ----------------------------------------------------------------------------------------------------------------------
def user_menu(collect_config_list):

    """
    This function is user interface for input and information
    """
    
    cmd_base_dir_name = "netcollect_cmd"
    timezone_name = "Asia/Ho_Chi_Minh"
    login_config_file_name = seed_file_name = ""
    cmd_dir_name = cmd_sub_dir_name = ""

    # User input
    print("\n{:-<120s}".format(r"[USER INPUT]"))

    print("")
    print("1. Network Information Collecting")
    print("2. Device Interactive Login")

    print("")
    while True:
        net_collect_mode = input("Enter your selection: ")
        if net_collect_mode in ["1", "2"]:
            break
        else:
            print("Invalid selection. Please try again!")

    print("")
    if collect_config_list:
        for i in range(len(collect_config_list)):
            print("{0}. {1}".format(i, collect_config_list[i]["name"]))
    print("{0}. {1}".format(len(collect_config_list), "Enter input filenames by yourself"))

    print("")
    while True:
        user_select = input("Enter your selection: ")
        try:
            user_select = int(user_select)
        except ValueError:
            continue
        
        if user_select in range(len(collect_config_list)):
            login_config_file_name = collect_config_list[user_select].get("login_config_file")
            seed_file_name = collect_config_list[user_select].get("device_seed_file")
            timezone_name = collect_config_list[user_select].get("timezone_name") or timezone_name
            break
        
        elif user_select == len(collect_config_list):
            print("")
            while True:
                login_config_file_name = input("Login configuration file name: ").strip()
                if login_config_file_name:
                    break
            while True:
                seed_file_name = input("Device seed file name: ").strip()
                if seed_file_name:
                    break
            break
        
        else:
            continue

    # Validate existence of input files
    if not os.path.isfile(login_config_file_name):
        print("\n* Login configuration file does not exist. Program exited!\n")
        sys.exit()

    if not os.path.isfile(seed_file_name):
        print("\n* Device seed file does not exist. Program exited!\n")
        sys.exit()

    if timezone_name not in all_timezones:
        print("\n* Timezone name does not exist. Program exited!\n")
        sys.exit()

    if net_collect_mode == "1":
        cmd_base_dir_name = os.path.join(os.path.split(seed_file_name)[0], cmd_base_dir_name)
        
        if os.path.isdir(cmd_base_dir_name):
            cmd_dir_name_list = [item for item in os.listdir(cmd_base_dir_name) if not item.startswith(r".")
                                 and os.path.isdir(os.path.join(cmd_base_dir_name, item))]
            if cmd_dir_name_list:
                print("")
                print("Command sub-directories:")

                for item_index, item in enumerate(cmd_dir_name_list):
                    print(" {0}. {1}".format(item_index, item))

                print("")
                while True:
                    user_select = input("Enter your selection: ")
                    try:
                        user_select = int(user_select)
                    except ValueError:
                        continue
                    if user_select in range(len(cmd_dir_name_list)):
                        cmd_sub_dir_name = cmd_dir_name_list[user_select]
                        cmd_dir_name = os.path.join(cmd_base_dir_name, cmd_sub_dir_name)
                        break
            
            else:
                cmd_dir_name = cmd_base_dir_name
        else:
            cmd_dir_name = os.path.split(seed_file_name)[0]

    return net_collect_mode, login_config_file_name, seed_file_name, cmd_dir_name, cmd_sub_dir_name, timezone_name


# ----------------------------------------------------------------------------------------------------------------------
def parse_files(net_collect_mode, login_config_file_name, seed_file_name, cmd_dir_name):

    # Parse and validate input files
    print("\n{:-<120s}".format(r"[INPUT FILES PARSING]"))
    print("")

    print("Login config file:", login_config_file_name)
    print("Device seed file:", seed_file_name)
    if net_collect_mode == "1":
        print("Command directory:", cmd_dir_name)

    print("")
    # Parse information of login config file
    parse_result, login_config_dict = parse_login_config(login_config_file_name)

    if not parse_result == "done":
        print("\nFailed parsing the configuration file, code:", parse_result)
        print("Program exiting...")
        sys.exit()

    jump_config = login_config_dict.get("jump")
    device_default_config = login_config_dict["device"]
    print("Parsing of login configuration file completed")

    # Parse information of device seed file
    parse_result, parse_dict = parse_seed_file(cmd_dir_name, seed_file_name, net_collect_mode)

    if parse_result != "done":
        print(parse_result, "Program exiting...")
        sys.exit()

    if not parse_dict:
        print("There is no valid information in device seed file. Program exiting...")
        sys.exit()

    print("Parsing of device seed file completed")

    # Process the parsed information
    for host in parse_dict:
        host_address = parse_dict[host]["address"]
        if jump_config and host_address in [jump_host["address"] for jump_host in jump_config]:
            print("{0:46s}: address is duplicated with jump host".format(host), "Program exiting...")
            sys.exit()

        host_config = dict(device_default_config)
        host_config.update(parse_dict[host]["login"])
        parse_dict[host]["login-hosts"] = jump_config + [host_config] if jump_config else [host_config]

    print("Processing of parsed information completed")

    return parse_dict


# ----------------------------------------------------------------------------------------------------------------------
def get_date_time(tz_name):
    if tz_name:
        date_time = datetime.datetime.now(timezone(tz_name))
    else:
        date_time = datetime.datetime.now()

    return date_time.strftime("%Y-%m-%dT%H-%M-%S")


# ----------------------------------------------------------------------------------------------------------------------
def net_collect(seed_file_name, cmd_sub_dir_name, parse_dict, timezone_name):

    """
    This function do network information collection by logging into each device to capture output
    """

    out_dir_name = "netcollect_log"

    print("\n{:-<120s}".format(r"[COLLECTION]"))
    print("The log file names are writen with time in the timezone:", timezone_name)
    user_select = input("Do you want to change the timezone name? (Press 'Y' to change): ").strip().upper()
    if user_select == "Y":
        print("Reference: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones")
        while True:
            timezone_name = input("Enter timezone name: ").strip()
            if timezone_name in all_timezones:
                break

    while True:
        max_concurrent_threads = input("\nMaximum concurrent collection [1-20]: ")
        if max_concurrent_threads.isdigit():
            max_concurrent_threads = int(max_concurrent_threads)
            if max_concurrent_threads in range(1, 21):
                break

    input("\nEnter to continue, Ctrl+C to exit...")

    # Create output directory
    date_time_str = get_date_time(timezone_name)
    out_dir_name = os.path.join(os.path.split(seed_file_name)[0], out_dir_name, cmd_sub_dir_name, date_time_str)

    if not os.path.isdir(out_dir_name):
        os.makedirs(out_dir_name)

    print("\nNetCollect log directory:", out_dir_name)

    # Login each network device and execute the commands
    all_host_list = sorted(parse_dict)

    thread_batch_end = 0
    while True:
        thread_list = []
        thread_batch_start = thread_batch_end
        thread_batch_end = thread_batch_end + max_concurrent_threads
        if thread_batch_end > len(all_host_list):
            thread_batch_end = len(all_host_list)

        host_batch = all_host_list[thread_batch_start:thread_batch_end]

        for host in host_batch:
            host_exec_list = parse_dict[host]["exec"]
            host_ping_list = parse_dict[host]["ping"]
            host_login_hosts = parse_dict[host]["login-hosts"]
            host_date_time_str = get_date_time(timezone_name)
            host_log_file_name = os.path.join(out_dir_name, "_".join([host_date_time_str, host]))
            device = Device(host, host_login_hosts, host_exec_list, host_ping_list)
            th = threading.Thread(target=device.log_capture, args=(host_log_file_name,))
            th.start()
            thread_list.append(th)
            time.sleep(0.5)

        for th in thread_list:
            th.join()

        if thread_batch_end == len(parse_dict):
            break

    return out_dir_name


# ----------------------------------------------------------------------------------------------------------------------
def net_interact(parse_dict):

    """
    This function do an interactive device login based on a menu selection
    """

    os.system("clear")
    print("")
    all_host_list = sorted(parse_dict)
    
    for host_index, host in enumerate(all_host_list):
        host_str = "{0}. {1} ({2})".format(host_index, host, parse_dict[host]["name"])
        if host_index % 3 != 2:
            print("{:<50}".format(host_str), end="")
            if host_index == len(all_host_list) - 1:
                print("")
        else:
            print("{:<50}".format(host_str))

    while True:
        host_selection = input("\nEnter your selection: ")
        if host_selection in [str(i) for i in range(len(all_host_list))]:
            break
        else:
            print("Invalid selection. Please try again!")

    host = all_host_list[int(host_selection)]
    host_login_hosts = parse_dict[host]["login-hosts"]
    device = Device(host, host_login_hosts)
    device.interact_login()


# ----------------------------------------------------------------------------------------------------------------------
class Device:

    """
    This is Device class for both information collecting and interactive login
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, name, login_hosts, exec_list=None, ping_list=None):
        self.name = name
        self.login_hosts = login_hosts
        self.exec_list = exec_list
        self.ping_list = ping_list
        self.__prompt = None
        self.__conn = None

    # ------------------------------------------------------------------------------------------------------------------
    def __logout(self):
        logout_timeout = 4  # in seconds
        if self.__conn:
            while self.__conn.isalive():
                self.__conn.sendline("exit")
                index = self.__conn.expect_exact([pexpect.EOF, pexpect.TIMEOUT, r"#", r"$", r">"], logout_timeout)
                if index == 0:
                    break
                elif index == 1:
                    self.__conn.sendline("\x03")
                    index = self.__conn.expect_exact([pexpect.EOF, pexpect.TIMEOUT, r"#", r"$", r">"], logout_timeout)
                    if index in [0, 1]:
                        break

        self.__conn = None
        self.__prompt = None

    # ------------------------------------------------------------------------------------------------------------------
    def __login(self):
        universal_delimiters = [r"#", r"$", r">"]
        login_timeout = 15  # in seconds
        conn = login_result = execute_prompt = None

        for host in self.login_hosts:
            mandatory_list = tuple(host.get(item) for item in ["address", "username", "prompt", "protocol"])
            optional_list = tuple(host.get(item) for item in ["port", "userident", "userpass", "cmd"])

            address, username, prompt, protocol = mandatory_list
            port, userident, userpass, cmd = optional_list

            if (not all(mandatory_list)) or (protocol not in ["ssh", "telnet"]):
                login_result = "invalid_config"
                print("{0:<46s} : failed login at {1}, code: {2}".format(self.name, host.get("name"), login_result))
                break

            # build login command string. ssh command is openssh-style
            if protocol == "ssh":
                cmd = cmd or "ssh"
                login_cmd_ident_str = " -i {0} ".format(userident) if userident else " "
                if port and port != "22":
                    login_cmd_str = "{0} -l {1} -p {2}".format(cmd, username, port) + login_cmd_ident_str + address
                else:
                    login_cmd_str = "{0} -l {1}".format(cmd, username) + login_cmd_ident_str + address

            else:
                cmd, port = cmd or "telnet", port or "23"
                login_cmd_str = "{0} {1} {2}".format(cmd, address, port)

            # print(login_cmd_str)
            # Spawn a new connection if it's not existing
            if not conn:
                first_hop = True
                conn = pexpect.spawn(login_cmd_str, encoding='utf-8')

            else:
                first_hop = False
                if protocol == "ssh" and not execute_prompt.endswith(r"$"):  # for ssh, only nix jump host supported
                    login_result = "failed_unsupported_jump"
                    print("{0:<46s} : failed login at {1}, code: {2}".format(self.name, host.get("name"), login_result))
                    break

                conn.sendline(login_cmd_str)

            # Handle the connection for login and authentication
            index = conn.expect([r'[Pp]assword:', prompt, pexpect.TIMEOUT, pexpect.EOF, r'[Uu]sername:',
                                 r'(?i)are you sure you want to continue connecting', r"Escape character is "],
                                login_timeout)

            if index == 6:  # device console login via terminal server
                login_result = "got_telnet_msg"
                conn.sendline('')
                index = conn.expect([r'[Pp]assword:', prompt, pexpect.TIMEOUT, pexpect.EOF, r'[Uu]sername:'],
                                    login_timeout)

            elif index == 5:
                login_result = "got_ssh_msg"
                conn.sendline('yes')
                index = conn.expect([r'[Pp]assword:', prompt, pexpect.TIMEOUT, pexpect.EOF, r'[Uu]sername:'],
                                    login_timeout)

            if index == 4:
                login_result = "got_username_prompt"
                conn.sendline(username)
                index = conn.expect([r'[Pp]assword:', prompt, pexpect.TIMEOUT, pexpect.EOF], login_timeout)

            if index == 3:
                login_result = "failed_eof"

            elif index == 2:
                login_result = "failed_connect" if not login_result else "failed_timeout"

            elif index == 1:
                login_result = "done" if first_hop or execute_prompt not in conn.after else "failed_connect"

            elif index == 0:
                conn.sendline(userpass)
                index = conn.expect([r'[Pp]assword:', prompt, pexpect.TIMEOUT, pexpect.EOF], login_timeout)
                result_code_list = ["failed_authen", "done", "failed_timeout", "failed_eof"]
                login_result = result_code_list[index]

            if login_result in ["failed_timeout", "failed_authen"] and conn.isalive():
                conn.sendline("\x03")

            if login_result == "done":
                conn.sendline("")
                conn.expect_exact(universal_delimiters)
                execute_prompt = conn.before.strip() + conn.after

            else:
                print("{0:<46s} : failed login at {1}, code: {2}".format(self.name, host.get("name"), login_result))
                break

        self.__conn = conn
        if login_result == "done" and conn and conn.isalive():
            self.__prompt = execute_prompt.split(r":")[-1] if execute_prompt.endswith("#") else ""
            print("{0:<15s} {1:<30s} : logged in successfully".format(self.name, self.__prompt[:-1]))

    # ------------------------------------------------------------------------------------------------------------------
    def interact_login(self):
        if not self.__conn:
            self.__login()
        elif self.__conn and not self.__prompt:
            self.__logout()
            self.__login()

        if self.__conn and not self.__prompt:
            self.__logout()
            print("\nDevice {0}: logged in unsuccessfully.".format(self.name), "Program exited!")
            sys.exit()
        elif self.__conn and self.__prompt:
            print("Enter to continue...")
            self.__conn.interact()

    # ------------------------------------------------------------------------------------------------------------------
    def log_capture(self, log_file_name):

        collect_timeout = 600  # in seconds

        if not self.__conn:
            self.__login()
        elif self.__conn and not self.__prompt:
            self.__logout()
            self.__login()

        if self.__conn and not self.__prompt:
            self.__logout()
        elif self.__prompt:
            log_file_name = "{0}_{1}.log".format(log_file_name, self.__prompt[:-1])
            log_file = open(log_file_name, "a+")
            self.__conn.logfile_read = log_file

            # Execute device exec command list
            if not self.exec_list:
                self.exec_list.extend([" "])

            for cmd in self.exec_list:
                if cmd != "":
                    self.__conn.sendline(cmd)
                    self.__conn.expect_exact(self.__prompt, timeout=collect_timeout)

            # Execute device ping list, to be developed later
            if self.ping_list:
                pass

            self.__conn.logfile_read = None
            log_file.close()
            print("{0:<15s} {1:<30s} : collection completed".format(self.name, self.__prompt))

            self.__logout()


# ----------------------------------------------------------------------------------------------------------------------
def main():
    """
    This function is the main program
    """

    os.system("clear")

    try:
        # find and parse NetCollect configuration files
        collect_config_list = []
        for filename in glob(os.path.dirname(os.path.realpath(__file__)) + r'/*.yml'):
            with open(filename, 'r') as collect_config_file:
                collect_config_list.extend(yaml.safe_load(collect_config_file))

        # user input
        (net_collect_mode, login_config_file_name, seed_file_name, cmd_dir_name,
         cmd_sub_dir_name, timezone_name) = user_menu(collect_config_list)

        # validate and parse input files
        parse_dict = parse_files(net_collect_mode, login_config_file_name, seed_file_name, cmd_dir_name)

        # device login and execution for NETWORK INFORMATION COLLECTING
        if net_collect_mode == "1":
            out_dir_name = net_collect(seed_file_name, cmd_sub_dir_name, parse_dict, timezone_name)

        # device login for NETWORK INTERACTIVE LOGIN
        elif net_collect_mode == "2":
            net_interact(parse_dict)

    except KeyboardInterrupt:
        print("\n\n* Program aborted by user. Exiting...\n")
        sys.exit()


# ----------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
