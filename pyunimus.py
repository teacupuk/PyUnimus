#!/usr/bin/env python3
import os
import sys
import base64
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("pyunimus.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Global variables (will be set during initialization)
devices = {}
script_dir = ""
backup_dir = ""

def error_check(status: int, message: str) -> None:
    """Check the exit status and exit the program if an error is detected.
    
    Args:
        status (int): The exit status code from a command.
        message (str): The error message to log and display if status is non-zero.
    """
    if status != 0:
        logger.error(message)
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
    url = f"{os.getenv('unimus_server_address').rstrip('/')}/api/v2/{api_endpoint}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {os.getenv('unimus_api_key')}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error("Unable to get data from unimus server")
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
        logger.error("Unable to perform unimus Status Check")
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
            logger.error(f"Failed to save backup for device {device_id}: {e}")

def get_all_devices() -> None:
    """Retrieve and store device information from the Unimus API.
    
    The function fetches device data page by page and populates the global 'devices' dictionary.
    """
    logger.info("Getting Device Information")
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
    logger.info(f"{backup_count} backups exported")

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
    logger.info(f"{backup_count} backups exported")

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
            logger.error(f"Command failed: {command}\nStdout: {result.stdout}\nStderr: {result.stderr}")
            sys.exit(result.returncode)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Command exception: {e}")
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
        protocol = os.getenv("git_server_protocol").lower()
        remote_url = ""
        if protocol == "ssh":
            run_command(f"ssh-keyscan -H {os.getenv('git_server_address')} >> ~/.ssh/known_hosts")
            if os.getenv("git_password", "") == "":
                remote_url = f"ssh://{os.getenv('git_username')}@{os.getenv('git_server_address')}/{os.getenv('git_repo_name')}"
            else:
                remote_url = f"ssh://{os.getenv('git_username')}:{os.getenv('git_password')}@{os.getenv('git_server_address')}/{os.getenv('git_repo_name')}"
        elif protocol in ["http", "https"]:
            remote_url = f"{protocol}://{os.getenv('git_username')}:{os.getenv('git_password')}@{os.getenv('git_server_address')}:{os.getenv('git_port')}/{os.getenv('git_repo_name')}"
        else:
            logger.error("Invalid setting for git_server_protocol")
            sys.exit(2)
        run_command(f"git remote add origin {remote_url}")
        run_command(f"git push -u origin {os.getenv('git_branch')} >> {log_file_path}")
        run_command("git push >> " + log_file_path)
    else:
        run_command("git add --all")
        commit_message = f"Unimus Git Extractor {datetime.now().strftime('%b-%d-%y %H:%M')}"
        run_command(f"git commit -m \"{commit_message}\"")
        run_command("git push")
    os.chdir(script_dir)

def import_variables() -> None:
    """Load and validate configuration variables from the .env file.
    
    The function reads the configuration from '.env', checks for mandatory keys, and populates the global config dictionary.
    
    Raises:
        SystemExit: If the configuration file is not found or required variables are missing.
    """
    """Load and validate configuration variables from the .env file."""
    load_dotenv(override=True)

    required_vars = ["unimus_server_address", "unimus_api_key", "backup_type", "export_type"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"{var} is not set in the environment")
            sys.exit(2)

    if os.getenv("export_type") == "git":
        git_vars = ["git_username", "git_email", "git_server_protocol",
                    "git_server_address", "git_port", "git_repo_name", "git_branch"]
        for var in git_vars:
            if not os.getenv(var):
                logger.error(f"{var} is not set in the environment")
                sys.exit(2)
        if os.getenv("git_server_protocol") in ["http", "https"] and not os.getenv("git_password"):
            logger.error("Please provide a git password in the environment")
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

    import_variables()

    status = unimus_status_check()

    if status == "OK":
        logger.info("Getting device data")
        get_all_devices()
        if os.getenv("backup_type") == "latest":
            logger.info("Exporting latest backups")
            get_latest_backups()
            logger.info("Export successful")
        elif os.getenv("backup_type") == "all":
            logger.info("Exporting all backups")
            get_all_backups()
            logger.info("Export successful")
        else:
            logger.warning("Unknown backup type specified")
        if os.getenv("export_type") == "git":
            logger.info("Pushing to git")
            push_to_git()
            logger.info("Push successful")
    else:
        if not status:
            logger.error("Unable to connect to unimus server")
            sys.exit(2)
        else:
            logger.error(f"Unimus server status: {status}")
            sys.exit(2)
            
    logger.info("Script finished")
    logger.info(f"Sleeping for {os.getenv('RUN_INTERVAL', '3600')} seconds")

if __name__ == "__main__":
    main()