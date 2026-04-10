# NetCollect - Network Device Information Collector & Interactive Login Tool

A Python-based automation tool for collecting network information from multiple Cisco, Juniper, Nokia, and Huawei devices via SSH/Telnet. Supports jump hosts, multi-threaded collection, and interactive device login.

## Overview

NetCollect is a network collection tool designed to:
- Collect device configuration and operational data from multiple network devices
- Support multiple jump hosts for reaching distant devices
- Enable interactive SSH/Telnet login to network devices
- Execute predefined command lists on devices
- Export collected data to timestamped log files
- Support Cisco, Juniper, Nokia, and Huawei router/switch platforms

## Features

- **Multi-Vendor Support**: Cisco, Juniper, Nokia, Huawei routers and switches
- **Flexible Authentication**: SSH and Telnet protocols with password/key authentication
- **Jump Host Support**: Multiple intermediate servers for accessing remote devices
- **Concurrent Collection**: Multi-threaded device access for faster collection
- **Flexible Command Execution**: Device-specific command files
- **Timezone Support**: Logging with proper timezone handling
- **Interactive Login**: Direct SSH/Telnet access to devices for manual operations
- **Configuration-Driven**: YAML-based configuration for easy management
- **Error Handling**: Comprehensive error codes and validation

## Requirements

### System Requirements
- macOS, Linux/Unix (pexpect does not support Windows natively)
- Python 3.x
- OpenSSH or SSH/Telnet client installed

### Python Dependencies
```
pexpect>=4.8.0        # Expect-like library for Python
ruamel.yaml>=0.17.0   # YAML parser preserving comments and structure
pytz>=2021.x          # Timezone support
```

## Installation

### 1. Clone or Download Repository
```bash
git clone <repository-url> network_collector_upgrade
cd network_collector_upgrade
```

### 2. Install Python Dependencies
```bash
# Using pip
pip install -r requirements.txt

# Or install manually
pip install pexpect ruamel.yaml pytz
```

### 3. Verify Installation
```bash
python3 netcollect.py
```

## Usage

### Basic Execution
```bash
python3 netcollect.py
```

### Interactive Menu

The program presents two main options:

```
1. Network Information Collecting
2. Device Interactive Login
```

## Configuration Files

### 1. NetCollect Config (netcollect_config.yml)

Main configuration file listing available projects:

```yaml
- name: "VNPT Pilot Project - Software Upgrade"
  login_config_file: "/path/to/login_config.yml"
  device_seed_file: "/path/to/device_list.csv"
  timezone_name: "Asia/Ho_Chi_Minh"  # Optional, default: Asia/Ho_Chi_Minh
```

**Fields**:
- `name`: Display name for the project
- `login_config_file`: Path to login configuration YAML file
- `device_seed_file`: Path to device CSV file
- `timezone_name`: Optional timezone (default: Asia/Ho_Chi_Minh)

### 2. Login Configuration (login_config.yml)

Defines jump hosts and device login parameters:

```yaml
jump:
  - name: 'jump-server-1'           # Optional, auto-generated if not specified
    address: '10.1.1.1'             # Mandatory
    protocol: 'ssh'                 # Optional, default: ssh
    port: '22'                      # Optional, default: 22 for ssh, 23 for telnet
    username: 'ubuntu'              # Mandatory
    userident: '~/.ssh/identity'    # Optional, SSH key path
    userpass: ''                    # Optional, password for jump host
    cmd: '/usr/bin/ssh'             # Optional, default: protocol name
    prompt: '@.*\$'                 # Mandatory, regex pattern for prompt

device:
  username: 'admin'                 # Mandatory
  userpass: 'password'              # Mandatory
  protocol: 'ssh'                   # Optional, default: ssh
  port: '22'                        # Optional, default: 22 for ssh, 23 for telnet
  cmd: '/usr/bin/ssh'               # Optional
  prompt: '\n.*#'                   # Optional, default: Cisco prompt
```

**Prompt Patterns by Vendor**:
- Cisco: `\n.*#` (default)
- Nokia: `\n.*#`
- Juniper: `@.*\>`
- Huawei: `\<.*\>`

### 3. Device Seed File (device_list.csv)

CSV file with device information (minimum 13 columns):

```csv
# address,command-file,ping-file,name,protocol,port,vendor,prompt,username,userpass,login-cmd,platform,software
10.1.1.1,commands.txt,,Router-A,ssh,22,cisco,,admin,password,,ASR1000,15.6
10.1.1.2,commands.txt,,Switch-B,ssh,22,cisco,,admin,password,,Catalyst3850,15.2
10.2.1.1,commands_juniper.txt,,JunOS-Router,ssh,22,juniper,,root,password,,MX480,17.2
192.168.1.1,,,Device-Manual,telnet,23,cisco,,user,pass,,C3750,12.2
```

**Column Definitions**:
| # | Column | Description | Required |
|---|--------|-------------|----------|
| 1 | address | IP address or hostname | Yes |
| 2 | command-file | Filename in cmd_base_dir (blank for no commands) | No |
| 3 | ping-file | Ping target file (comma-separated targets) | No |
| 4 | name | Device name/label | Yes |
| 5 | protocol | ssh or telnet | No (default: ssh) |
| 6 | port | SSH port (22) or Telnet port (23) | No |
| 7 | vendor | cisco, juniper, nokia, huawei | Yes |
| 8 | prompt | Custom prompt regex (empty = vendor default) | No |
| 9 | username | Login username | No (uses default) |
| 10 | userpass | Login password | No (uses default) |
| 11 | login-cmd | Custom SSH/Telnet command | No |
| 12 | platform | Device platform (informational) | No |
| 13 | software | Software version (informational) | No |

### 4. Command Files

Text files containing commands to execute on devices:

**Example: commands.txt**
```
show version
show running-config
show interfaces
show ip route
show bgp summary
```

**Rules**:
- One command per line
- Lines starting with `#` are treated as comments and skipped
- Blank lines are ignored
- Commands are executed sequentially

### 5. Directory Structure

```
network_collector_upgrade/
├── netcollect.py                    # Main script
├── netcollect_config.yml            # NetCollect configuration (multiple projects)
├── netcollect/
│   ├── Project1/
│   │   ├── login_config.yml         # Login configuration
│   │   ├── device_list.csv          # Device seed file
│   │   ├── netcollect_cmd/          # Command directory
│   │   │   ├── commands_set1/
│   │   │   │   ├── commands.txt
│   │   │   │   └── commands_juniper.txt
│   │   │   └── commands_set2/
│   │   └── netcollect_log/          # Output logs (auto-created)
│   │       └── commands_set1/
│   │           └── 2024-04-09T14-25-30/
│   │               ├── 2024-04-09T14-25-30_device1_ssh22.log
│   │               └── 2024-04-09T14-25-30_device2_ssh22.log
│   └── Project2/
│       └── ...
```

## Workflow

### Mode 1: Network Information Collection

1. **Configuration Selection**: Choose project or enter file paths manually
2. **File Validation**: Verify login configuration and device seed files exist
3. **Command Set Selection**: Select which command set to run
4. **Collection Parameters**:
   - Timezone selection (for log timestamps)
   - Maximum concurrent threads (1-20)
5. **Execution**: Program logs into each device and executes commands
6. **Output**: Timestamped log files per device

### Mode 2: Interactive Device Login

1. **Device Selection**: Choose device from list
2. **Interactive Session**: Direct SSH/Telnet access to device
3. **Manual Operations**: Execute commands interactively
4. **Exit**: Type `exit` to disconnect

## Output Files

### Log File Structure

**Location**: `device_seed_dir/netcollect_log/command_set/YYYY-MM-DDTHH-MM-SS/`

**Filename Format**: `YYYY-MM-DDTHH-MM-SS_devicename_protocolport.log`

**Example**:
```
2024-04-09T14-25-30_router-a_ssh22.log
2024-04-09T14-25-30_switch-b_ssh22.log
2024-04-09T14-25-30_junos-router_ssh22.log
```

**Log Content**:
```
show version
Cisco IOS Software, ASR1000 Software, Version 15.6(2)S5

Copyright (c) 1986-2017 by Cisco Systems, Inc.

show running-config
Building configuration...

Current configuration : 15432 bytes
...
```

## Authentication Methods

### SSH with Password
```yaml
protocol: 'ssh'
username: 'admin'
userpass: 'password123'
```

### SSH with Key
```yaml
protocol: 'ssh'
username: 'admin'
userident: '~/.ssh/id_rsa'  # Key path
userpass: ''                 # Leave empty
```

### Telnet with Password
```yaml
protocol: 'telnet'
port: '23'
username: 'user'
userpass: 'password'
```

## Multi-Hop Jump Host Configuration

Enable access to devices behind jump servers:

```yaml
jump:
  - name: 'bastion1'
    address: '203.0.113.1'
    protocol: 'ssh'
    username: 'ubuntu'
    userpass: 'jumppass'
    prompt: '@.*\$'          # Linux prompt

  - name: 'bastion2'
    address: '10.0.0.1'
    protocol: 'ssh'
    username: 'root'
    userpass: 'pass2'
    prompt: '@.*#'

device:
  username: 'admin'
  userpass: 'devicepass'
  prompt: '\n.*#'
```

**Flow**:
User → SSH to bastion1 → SSH to bastion2 → SSH to device

## Threading & Performance

### Concurrent Execution

The program supports 1-20 concurrent device connections for faster collection.

**Recommendations**:
- Small network (5-10 devices): 2-5 threads
- Medium network (10-30 devices): 5-10 threads
- Large network (30+ devices): 10-20 threads

### Performance Optimization

1. **Command Optimization**: Minimize commands per device
2. **Timeout Tuning**: Adjust login timeout for slow networks
3. **Thread Count**: Balance between speed and system load

## Error Codes

| Code | Meaning | Resolution |
|------|---------|-----------|
| `failed_invalid_jump_config` | Jump host configuration missing mandatory fields | Verify address, username, prompt in jump section |
| `failed_duplicate_jump_address` | Duplicate jump host address | Remove duplicate jump host entry |
| `failed_invalid_device_config` | Device config missing username/password | Ensure device section has username and userpass |
| `failed_invalid_seed_file` | CSV has fewer than 13 columns | Add missing columns to CSV |
| `failed_connect` | Cannot connect to device | Verify IP, port, firewall rules |
| `failed_authen` | Authentication failure | Verify username and password |
| `failed_timeout` | Connection timeout | Increase timeout, check network |
| `failed_eof` | Connection closed unexpectedly | Check device status and firewall |
| `failed_unsupported_jump` | Jump host is not Unix-like | Use Linux/Unix-based jump servers |

## Troubleshooting

### Script won't execute
```bash
# Verify Python version
python3 --version

# Check dependencies
pip list | grep -E "pexpect|ruamel|pytz"

# Make script executable
chmod +x netcollect.py
```

### Login failures

1. **Verify device is reachable**:
   ```bash
   ping 10.1.1.1
   ssh -v admin@10.1.1.1
   ```

2. **Check credentials**:
   - Verify username/password in login_config.yml
   - Test manual SSH/Telnet login

3. **Validate prompts**:
   - Run `ssh admin@device` manually
   - Check actual prompt pattern
   - Update prompt regex if needed

4. **Timeout issues**:
   - Increase `login_timeout` in code (line ~570)
   - Reduce command count in command files
   - Check network latency

### No output files created

1. **Verify command directory exists**: `ls -la netcollect_cmd/`
2. **Check device_list.csv format**: Ensure 13+ columns
3. **Review error messages**: Look for login failures
4. **Verify disk space**: Ensure sufficient space in output directory

### Incorrect log timestamps

1. **Verify timezone**: Timezone name must be from IANA database
2. **Check system clock**: `date` should show correct time
3. **List valid timezones**: Reference [List of tz database time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

## Example Workflows

### Scenario 1: Collect from Cisco devices behind jump host

**Setup**:
1. Create `login_config.yml` with jump host and Cisco device defaults
2. Create `device_list.csv` with Cisco device IPs and vendor='cisco'
3. Create `commands.txt` with show commands
4. Run netcollect.py → Select collection → Select command set

### Scenario 2: Mixed vendor environment

**Setup**:
1. Create separate command files: `cisco_commands.txt`, `juniper_commands.txt`
2. In `device_list.csv`, specify command file per device
3. Create vendor-specific sections in `login_config.yml` if needed
4. Run program and select appropriate command set

### Scenario 3: Emergency manual access to failed device

**Setup**:
1. Run netcollect.py → Select interactive login
2. Choose device from menu
3. Execute manual troubleshooting commands
4. Exit when done

## Advanced Usage

### Custom Command Execution

Edit device_list.csv to use different command files per device:

```csv
10.1.1.1,cisco_extended_commands.txt,,Router-A,ssh,22,cisco
10.2.1.1,juniper_commands.txt,,JunOS-Device,ssh,22,juniper
10.3.1.1,minimal_commands.txt,,Simple-Device,ssh,22,cisco
```

### Timezone-Aware Logging

Logs are created with timestamps in specified timezone:

```
2024-04-09T14-25-30  # Asia/Ho_Chi_Minh
2024-04-09T06-25-30  # UTC (same moment, different timezone)
```

### Batch Collection

Run collection against multiple projects sequentially:

```bash
for config in project1 project2 project3; do
    # Edit netcollect_config.yml to select project
    python3 netcollect.py
done
```

## Limitations

1. **Windows Support**: pexpect doesn't support Windows (use WSL or Linux VM)
2. **Jump Host Chain**: Limited to sequential jump hosts (not parallel)
3. **Timeout Fixed**: Hardcoded timeouts (600s collection, 15s login, 4s logout)
4. **Ping Feature**: Placeholder only, not implemented
5. **Device Types**: Primarily tested with Cisco devices

## Future Enhancements

- [ ] Implement ping functionality
- [ ] Add device-level timeout configuration
- [ ] Support Windows via alternative libraries
- [ ] JSON/XML output formats
- [ ] REST API integration
- [ ] Ansible integration
- [ ] Database storage option
- [ ] Web UI for configuration

## Security Considerations

1. **Credentials**: Store in secure configuration files with restricted permissions
   ```bash
   chmod 600 login_config.yml device_list.csv
   ```

2. **SSH Keys**: Use key-based authentication when possible
   ```yaml
   userident: '~/.ssh/id_rsa'
   ```

3. **Passwords**: Use SSH keys instead of passwords for production

4. **Log Files**: May contain sensitive information
   ```bash
   chmod 600 netcollect_log/*
   ```

## Dependencies Summary

```
netcollect.py:
  ├── pexpect         # Expect-like spawn/interact
  ├── ruamel.yaml     # YAML configuration parsing
  ├── pytz            # Timezone handling
  ├── threading       # Concurrent device access
  ├── os, sys         # System utilities
  ├── datetime        # Timestamp generation
  └── glob            # File pattern matching
```

## Version History

- **v2.0** (2024-04): Upgrade version
  - Multi-threading support
  - Vendor-specific prompt handling
  - Multiple jump host support
  - Enhanced error handling

## Original Author

Developed by Sanh (savu)

## Support & References

- Pexpect documentation: https://pexpect.readthedocs.io/
- Ruamel.yaml: https://yaml.readthedocs.io/
- IANA Timezone Database: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
- Cisco CLI Reference: https://www.cisco.com/

## License

As specified by original author or organization

---

**Last Updated**: April 2024
**Location**: `/network_collector_upgrade/netcollect.py`
