import os
import requests
import json
import zipfile
from datetime import datetime

NITRADO_API_BASE_URL='https://api.nitrado.net/services/'

class NitradoAPI:
    def __init__(self, token, nitrado_id, server_id, remote_base_path, ssl_verify=True):
        self.token = token
        self.nitrado_id = nitrado_id
        self.server_id = server_id
        self.headers = {'Authorization': f'Bearer {token}'}
        self.remote_base_path = remote_base_path
        self.ssl_verify = ssl_verify
        
    def download_file(self, file_path):
        """Download file from server"""
        try:
            url = f'{NITRADO_API_BASE_URL}{self.nitrado_id}{self.remote_base_path}/download?file={file_path}'
            print(f"Downloading from Nitrado: {url}")
            response = requests.get(url, headers=self.headers, verify=self.ssl_verify)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 404:
                print(f"ERROR: Required remote file not found: {file_path}")
                print("Aborting deployment for safety.")
                return None
            else:
                print(f"Error downloading {file_path}: {response.text}")
                return None
        except Exception as e:
            print(f"Download error: {str(e)}")
        return None
    
    def backup_files(self, modified_files):
        print("Backing up modified files...")
        """Backup modified files"""
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_zip_path = os.path.join(backup_dir, f'backup_{timestamp}.zip')
        
        with zipfile.ZipFile(backup_zip_path, 'w') as backup_zip:
            for file in modified_files:
                content = self.download_file(file['remote_path'])
                if content:
                    backup_zip.writestr(file['name'], content)
        
        if not backup_zip.namelist():
            print("No files could be downloaded. Backup zip is empty.")
            return False
        
        print(f"Backup created at {backup_zip_path}")
        return True
            
    def upload_file(self, remote_path, filename, content):
        print(f"Uploading to Nitrado {filename} to {remote_path}")
        try:
            url = f'{NITRADO_API_BASE_URL}{self.nitrado_id}{self.remote_base_path}/upload'
            files = {
                'file': content
            }
            params = {
                'path': remote_path,
                'file': filename
            }
            return True
            response = requests.post(
                url,
                headers=self.headers,
                data=params,
                files=files,
                verify=self.ssl_verify
                )
            if response.status_code == 200:
                print(f"Successfully uploaded to {remote_path}")
                return True
            else:
                print(f"Upload error: {response.text}")
                return False
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return False
            
    def restart_server(self):
        print("Restarting server...")
        try:
            url = f'{NITRADO_API_BASE_URL}{self.nitrado_id}/gameservers/restart'
            response = requests.post(url, headers=self.headers, verify=self.ssl_verify)
            if response.status_code == 200:
                print("Server restart initiated")
                return True
            else:
                print(f"Restart error: {response.text}")
                return False
        except Exception as e:
            print(f"Restart error: {str(e)}")
            return False
    
    def get_file_stats(self, remote_dirs):
        print(f"Get file information from Nitrado...")
        base_path = f"/games/{self.server_id}/ftproot/dayzxb_missions/dayzOffline.chernarusplus/"

        try:
            # Get file stats from the main directory
            url = f'{NITRADO_API_BASE_URL}{self.nitrado_id}{self.remote_base_path}/list?dir={base_path}'
            response = requests.get(url, headers=self.headers, verify=self.ssl_verify)
            
            if response.status_code == 200:
                response_json = response.json()
                file_stats = [
                    {
                        'path': file['path'],
                        'modified_at': datetime.fromtimestamp(file['modified_at']).isoformat(),
                        'name': file['name']
                    }
                    for file in response_json['data']['entries'] if file['type'] == 'file'
                ]
            elif response.status_code == 404:
                print("ERROR: Main directory not found.")
                return None
            else:
                print(f"Error fetching file stats: {response.text}")
                return None
            
            # Get file stats from each remote directory
            for remote_dir in remote_dirs:
                dir_url = f'{NITRADO_API_BASE_URL}{self.nitrado_id}{self.remote_base_path}/list?dir={base_path}/{remote_dir}'
                dir_response = requests.get(dir_url, headers=self.headers, verify=self.ssl_verify)
                if dir_response.status_code == 200:
                    dir_response_json = dir_response.json()
                    file_stats.extend([
                        {
                            'path': file['path'],
                            'modified_at': datetime.fromtimestamp(file['modified_at']).isoformat(),
                            'name': file['name']
                        }
                        for file in dir_response_json['data']['entries'] if file['type'] == 'file'
                    ])
                elif dir_response.status_code == 404:
                    print(f"ERROR: Directory not found: {remote_dir}")
                    return None
                else:
                    print(f"Error fetching file stats from {remote_dir}: {dir_response.text}")
                    return None
            print(f"Successfully fetched {len(file_stats)} file stats")
            return file_stats
        except Exception as e:
            print(f"Download error: {str(e)}")
        return None

def compare_files(files_rep, files_remote):
    print(f"Compare modifed date local and remote files...")
    modified_files = []
    for local_file in files_rep:
        local_name = local_file['name']
        local_modified_at = datetime.fromisoformat(local_file['modified_at'])
        for remote_file in files_remote:
            remote_name = remote_file['name']
            if remote_name == local_name:
                remote_modified_at = datetime.fromisoformat(remote_file['modified_at'])
                if local_modified_at > remote_modified_at:
                    modified_files.append({
                        'local_path': local_file['path'],
                        'remote_path': remote_file['path'],
                        'local_modified_at': local_modified_at.isoformat(),
                        'remote_modified_at': remote_modified_at.isoformat(),
                        'name': local_name
                    })
                break
    print(f"Found {len(modified_files)} modified files")
    return modified_files

def scan_repository_files(deploy_directory):
    """Scan all files in the repository"""
    print(f"Scanning repository files in {deploy_directory}...")
    files_to_check = []
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), deploy_directory)

    # Walk through all files in the deploy directory
    for root, _, files in os.walk(base_dir):
        # Skip hidden directories
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
            
        for file in files:
            # Skip hidden files and deploy config
            if file.startswith('.') or file == 'deploy-config.json' or file.endswith('.py'):
                continue
                
            # Make path relative to deploy directory
            rel_path = os.path.relpath(os.path.join(root, file), base_dir)
            
            # Get file stats
            file_stats = os.stat(os.path.join(root, file))
            modified_at = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            files_to_check.append({
                'path': rel_path,  # e.g. 'db/events.xml'
                'modified_at': modified_at,
                'name': file
            })
    print(f"Found {len(files_to_check)} files to process")
    return files_to_check

def main():
    # Initialize API
    #api = NitradoAPI(
     #   os.environ['NITRADO_API_TOKEN'],
      #  os.environ['NITRADO_ID'],
       # os.environ['SERVER_ID']
    #)

    # Load config for restart setting
    try:
        with open('deploy-config.json', 'r') as f:
            config = json.load(f)
            restart_after_deploy = config.get('restart_after_deploy', True)
            remote_dirs = config.get('remote_dirs', [])
            remote_base_path = config.get('remote_base_path', '/gameservers/file_server/')
            ssl_verify = config.get('ssl_verify', True)
            deploy_directory = config.get('deploy_directory', 'chernarus_boosted_customevents_bunker_console')
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return False
    
    api = NitradoAPI(
        'M8qp_kcGLejWdkFG4vx9cu8fD02VRiEweegScYjBs9tU5emUS6DV6L9msaucEV0sC2RjZQVZr8ORvtUWuEO7_1VGq3SCFM3wGU-I',
        '16355842',
        'ni8292907_1',
        remote_base_path,
        ssl_verify
    )
    
    # Scan repository for files
    files_rep = scan_repository_files(deploy_directory)
    if not files_rep:
        print("No local files found to process")
        return False
    
    #Get remote file information from Nitrado
    files_remote = api.get_file_stats(remote_dirs)
    if not files_remote:
        print("No remote files found to process")
        return False

    # Compare files
    modified_files = compare_files(files_rep, files_remote)
    if not modified_files:
        print("No files modified. Skipping deployment.")
        return True
    
    # Backup remote files
    if not api.backup_files(modified_files):
        print("Backup failed. Aborting deployment.")
        return False

    # Upload changed files
    for file in modified_files:
        local_path = file['local_path']
        remote_path = file['remote_path']
        
        with open(local_path, 'rb') as f:
            content = f.read()
        
        if not api.upload_file(remote_path, file['name'], content):
            print(f"Failed to upload {local_path}")
            return False
    print("All modified files uploaded successfully.")

    # Restart server
    if(restart_after_deploy):
        if not api.restart_server():
            print("Failed to restart server")
            return False
        print("Server restart initiated")
    
    return True

if __name__ == "__main__":
    main()