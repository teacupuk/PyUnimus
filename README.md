# PyUnimus

pyunimus is a Python-based tool that automates the backup export process from a Unimus server to your local disk or Git repository. Originally derived from a Bash script, this tool leverages the Unimus API to fetch device backups and supports exporting either the latest backup or all available backups. Additionally, if configured, it can push the backups to a Git repository for version control and backup management.

## Features

- **Device Backup Export:**  
  Retrieve backup data from Unimus for one or more devices.

- **Backup Types:**  
  Choose between exporting only the latest backup or all available backups.

- **Git Integration:**  
  Optionally push backups to a remote Git repository using protocols like SSH, HTTP, or HTTPS.

## Prerequisites

- **Python 3.x:**  
  Ensure you have Python 3 installed. You can download it from [python.org](https://www.python.org/).

- **Required Python Packages:**  
  Install the required packages using pip:
  ```bash
  pip3 install requests
  ```

- **Git:**  
  If you plan to use Git integration, make sure Git is installed on your system and properly configured in your PATH.

## Installation

**Clone the Repository:**
   ```bash
   git clone https://github.com/teacupuk/pyunimus.git
   cd pyunimus
   ```

## Configuration

The tool is configured through the `config.json` file (converted from an ENV file). Update the JSON file with your settings before running the tool:

```json
{
  "unimus_server_address": "http://foo.bar:8085",
  "unimus_api_key": "insert api key here",
  "backup_type": "latest",
  "export_type": "fs",
  "git_username": "foo",
  "git_password": "password",
  "git_email": "foo@bar.org",
  "git_server_protocal": "ssh",
  "git_server_address": "192.168.4.5",
  "git_port": "22",
  "git_repo_name": "user/PyUnimus",
  "git_branch": "master"
}
```

> **Note:**  
> - Ensure all mandatory keys are filled in.  
> - For Git integration, adjust the settings for your preferred protocol (SSH, HTTP, or HTTPS).

## Usage

1. **Run the Script:**
   Execute the script using Python:
   ```bash
   python unimus-backup-exporter.py
   ```

2. **Logging:**
   The tool writes log messages to `pyunimus.log` located in the same directory as the script.

3. **Backup Directory:**
   Backups are saved in the `backups` folder. Each device gets its own folder containing its respective backup files.

## How It Works

- **API Interaction:**  
  The script makes GET requests to the Unimus API using the configured API key and server address.  
- **Data Handling:**  
  Device and backup information are fetched using paginated API calls; backups are decoded from base64 and stored on disk.
- **Git Operations:**  
  When configured for Git export, the script initializes a Git repository (if one does not exist), commits the changes, and pushes the backups to the remote repository.

## Contributing

Contributions and feedback are welcome! If you find an issue or have suggestions, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.

## Acknowledgments

- Original Bash implementation that inspired this Python version.
- The Unimus API and community for providing inspiration and support.

---

Enjoy using pyunimus to keep your backups safe and version-controlled!
