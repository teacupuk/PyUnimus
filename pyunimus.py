#!/usr/bin/env python3
import os
import sys
import json
import base64
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# ANSI color codes
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
RESET = "\033[0m"

# Global variables (will be set during initialization)
config = {}
devices = {}
script_dir = ""
backup_dir = ""
log_file_path = ""

def write_log(message: str) -> None:
    """Append a message to the log file with a timestamp.
    
    Args:
        message (str): The message to append.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, "a") as log_file:
        log_file.write(f"{timestamp} {message}\n")

def echo_green(message: str) -> None:
    """Log and print a message in green.
    
    The function writes the message to the log file and prints it to the console with green color.
    
    Args:
        message (str): The message to output.
    """
    write_log(message)
    print(f"{GREEN}{message}{RESET}")

def echo_yellow(message: str) -> None:
    """Log and print a warning message in yellow.
    
    The function prefixes the message with 'WARNING:', writes it to the log file, and prints it in yellow.
    
    Args:
        message (str): The warning message to output.
    """
    write_log("WARNING: " + message)
    print(f"{YELLOW}WARNING: {message}{RESET}")

def echo_red(message: str) -> None:
    """Log and print an error message in red.
    
    The function prefixes the message with 'ERROR:', writes it to the log file, and prints it in red.
    
    Args:
        message (str): The error message to output.
    """
    write_log("ERROR: " + message)
    print(f"{RED}ERROR: {message}{RESET}")

def error_check(status: int, message: str) -> None:
    """Check the exit status and exit the program if an error is detected.
    
    Args:
        status (int): The exit status code from a command.
        message (str): The error message to log and display if status is non-zero.
    """
    if status != 0:
        echo_red(message)
        sys.exit(status)

def unimus_get(api_endpoint: str) -> dict:
    """Fetch JSON data from the Unimus API for a given endpoint.
    
    Constructs the URL using the base server address from the configuration and sends an HTTP GET request.
    
    Args:
        api_endpoint (str): The API endpoint to query (e.g., 'health', 'devices?page=0').
    
    Returns:
        dict: The JSON response as a dictionary.
    
    Raises:
        SystemExit: If the HTTP request fails.
    """
    url = f"{config['unimus_server_address'].rstrip('/')}/api/v2/{api_endpoint}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config['unimus_api_key']}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        echo_red("Unable to get data from unimus server")
        sys.exit(1)
    return response.json()

def unimus_status_check() -> str:
    """Check the health status of the Unimus server.
    
    Returns:
        str: The status of the Unimus server as obtained from the API.
    
    Raises:
        SystemExit: If the status cannot be retrieved.
    """
    result = unimus_get("health")
    try:
        status = result["data"]["status"]
    except (KeyError, TypeError):
        echo_red("Unable to perform unimus Status Check")
        sys.exit(1)
    return status

def save_backup(device_id, backup_date, backup_b64, bkp_type) -> None:
    """Save a backup for a device by decoding a base64-encoded string and writing it to disk.
    
    The backup is saved in a directory named using the device's address and ID. The file extension is determined by the backup type.
    
    Args:
        device_id: The identifier for the device.
        backup_date: The backup date as a formatted string.
        backup_b64: The backup data encoded in base64.
        bkp_type: The type of backup ('TEXT' for text files, otherwise binary is assumed).
    """
    address = devices.get(device_id, f"device-{device_id}")
    ext = "txt" if bkp_type.upper() == "TEXT" else "bin"
    # Directory for the device backups
    device_dir = Path(backup_dir) / f"{address} - {device_id}"
    device_dir.mkdir(parents=True, exist_ok=True)
    # Construct backup file name
    file_name = f"Backup {address} {backup_date} {device_id}.{ext}"
    backup_file = device_dir / file_name
    if not backup_file.exists():
        try:
            backup_data = base64.b64decode(backup_b64)
            with open(backup_file, "wb") as f:
                f.write(backup_data)
        except Exception as e:
            echo_red(f"Failed to save backup for device {device_id}: {e}")

def get_all_devices() -> None:
    """Retrieve and store device information from the Unimus API.
    
    The function fetches device data page by page and populates the global 'devices' dictionary.
    """
    echo_green("Getting Device Information")
    page = 0
    while True:
        result = unimus_get(f"devices?page={page}")
        data_list = result.get("data", [])
        if not data_list:
            break
        for item in data_list:
            device_id = item.get("id")
            address = item.get("address")
            if device_id and address:
                devices[device_id] = address
        page += 1

def get_all_backups() -> None:
    """Fetch and save all backups for each device from the Unimus API.
    
    Iterates through each device and their respective paginated backups, saving each backup to disk.
    """
    backup_count = 0
    for device_id in devices.keys():
        page = 0
        while True:
            result = unimus_get(f"devices/{device_id}/backups?page={page}")
            data_list = result.get("data", [])
            if not data_list:
                break
            for item in data_list:
                tme = item.get("validSince")
                if tme:
                    backup_date = datetime.fromtimestamp(tme).strftime("%Y-%m-%d-%H:%M:%S")
                else:
                    backup_date = "unknown"
                backup_b64 = item.get("bytes", "")
                bkp_type = item.get("type", "")
                save_backup(device_id, backup_date, backup_b64, bkp_type)
                backup_count += 1
            page += 1
    echo_green(f"{backup_count} backups exported")

def get_latest_backups() -> None:
    """Fetch and save the latest backups for all devices from the Unimus API.
    
    Iterates through pages of the latest backups and saves each one to disk.
    """
    backup_count = 0
    page = 0
    while True:
        result = unimus_get(f"devices/backups/latest?page={page}")
        data_list = result.get("data", [])
        if not data_list:
            break
        for item in data_list:
            device_id = item.get("deviceId")
            backup_info = item.get("backup", {})
            tme = backup_info.get("validSince")
            if tme:
                backup_date = datetime.fromtimestamp(tme).strftime("%Y-%m-%d-%H:%M:%S")
            else:
                backup_date = "unknown"
            backup_b64 = backup_info.get("bytes", "")
            bkp_type = backup_info.get("type", "")
            save_backup(device_id, backup_date, backup_b64, bkp_type)
            backup_count += 1
        page += 1
    echo_green(f"{backup_count} backups exported")

def run_command(command, cwd=None) -> str:
    """Execute a shell command and return its output.
    
    Args:
        command (str): The shell command to execute.
        cwd (str, optional): The working directory to run the command in. Defaults to None.
    
    Returns:
        str: Standard output from the command, stripped of whitespace.
    
    Raises:
        SystemExit: If the command execution fails.
    """
    try:
        result = subprocess.run(command, cwd=cwd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            echo_red(f"Command failed: {command}\nStdout: {result.stdout}\nStderr: {result.stderr}")
            sys.exit(result.returncode)
        return result.stdout.strip()
    except Exception as e:
        echo_red(f"Command exception: {e}")
        sys.exit(1)

def push_to_git() -> None:
    """Push local backups to the remote Git repository.
    
    If the backup directory is not a Git repository, it initializes one, adds the remote, commits the changes, and pushes.
    
    Raises:
        SystemExit: If any Git command fails.
    """
    os.chdir(backup_dir)
    try:
        inside_repo = run_command("git rev-parse --is-inside-work-tree")
    except Exception:
        inside_repo = ""
    if not inside_repo:
        run_command("git init")
        run_command("git add .")
        run_command("git commit -m 'Initial Commit'")
        protocol = config.get("git_server_protocol", "").lower()
        remote_url = ""
        if protocol == "ssh":
            run_command(f"ssh-keyscan -H {config['git_server_address']} >> ~/.ssh/known_hosts")
            if config.get("git_password", "") == "":
                remote_url = f"ssh://{config['git_username']}@{config['git_server_address']}/{config['git_repo_name']}"
            else:
                remote_url = f"ssh://{config['git_username']}:{config['git_password']}@{config['git_server_address']}/{config['git_repo_name']}"
        elif protocol in ["http", "https"]:
            remote_url = f"{protocol}://{config['git_username']}:{config['git_password']}@{config['git_server_address']}:{config['git_port']}/{config['git_repo_name']}"
        else:
            echo_red("Invalid setting for git_server_protocol")
            sys.exit(2)
        run_command(f"git remote add origin {remote_url}")
        run_command(f"git push -u origin {config['git_branch']} >> {log_file_path}")
        run_command("git push >> " + log_file_path)
    else:
        run_command("git add --all")
        commit_message = f"Unimus Git Extractor {datetime.now().strftime('%b-%d-%y %H:%M')}"
        run_command(f"git commit -m \"{commit_message}\"")
        run_command("git push")
    os.chdir(script_dir)

def import_variables() -> None:
    """Load and validate configuration variables from the config.json file.
    
    The function reads the configuration from 'config.json', checks for mandatory keys, and populates the global config dictionary.
    
    Raises:
        SystemExit: If the configuration file is not found or required variables are missing.
    """
    global config
    config_file = Path(script_dir) / "config.json"
    if not config_file.exists():
        echo_red(f"Configuration file {config_file} not found")
        sys.exit(2)
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
    except Exception as e:
        echo_red(f"Failed to load configuration: {e}")
        sys.exit(2)

    required_vars = ["unimus_server_address", "unimus_api_key", "backup_type", "export_type"]
    for key in required_vars:
        if not config.get(key):
            echo_red(f"{key} is not set in the configuration")
            sys.exit(2)
    if config["export_type"] == "git":
        git_vars = ["git_username", "git_email", "git_server_protocol",
                    "git_server_address", "git_port", "git_repo_name", "git_branch"]
        for key in git_vars:
            if not config.get(key):
                echo_red(f"{key} is not set in the configuration")
                sys.exit(2)
        if config["git_server_protocol"] in ["http", "https"] and not config.get("git_password"):
            echo_red("Please provide a git password in the configuration")
            sys.exit(2)

def main() -> None:
    """Main entry point for the pyunimus backup exporter.
    
    Sets up directories, loads configuration, checks the Unimus server status, retrieves backups, and optionally pushes to Git.
    Exits the program if any step fails.
    """
    global script_dir, backup_dir, log_file_path
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    backup_dir = os.path.join(script_dir, "backups")
    Path(backup_dir).mkdir(exist_ok=True)
    log_file_path = os.path.join(script_dir, "pyunimus.log")
    with open(log_file_path, "a") as f:
        f.write("Log File - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")

    import_variables()
    status = unimus_status_check()
    if status == "OK":
        echo_green("Getting device data")
        get_all_devices()
        if config["backup_type"] == "latest":
            echo_green("Exporting latest backups")
            get_latest_backups()
            echo_green("Export successful")
        elif config["backup_type"] == "all":
            echo_green("Exporting all backups")
            get_all_backups()
            echo_green("Export successful")
        else:
            echo_yellow("Unknown backup type specified")
        if config["export_type"] == "git":
            echo_green("Pushing to git")
            push_to_git()
            echo_green("Push successful")
    else:
        if not status:
            echo_red("Unable to connect to unimus server")
            sys.exit(2)
        else:
            echo_red(f"Unimus server status: {status}")
            sys.exit(2)
    echo_green("Script finished")

if __name__ == "__main__":
    main()