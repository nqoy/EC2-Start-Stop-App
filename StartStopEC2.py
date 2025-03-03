import sys
import time
import subprocess
import json
import boto3
import tkinter as tk
import threading
import os
from dotenv import dotenv_values

isRunningAction = False
env_vars = dotenv_values(".env")

def expand(value):
    return value.format(**env_vars) if value else value

env_vars = {key: expand(value) for key, value in env_vars.items()}

def get_base_path():
    if getattr(sys, 'frozen', False):
        # If running as a bundled executable (e.g., via PyInstaller), use the extracted folder
        return sys._MEIPASS
    else:
        # If running as a script, use the current working directory
        return os.path.dirname(__file__)

def get_aws_credentials():
    try:
        # Check if running as a bundled executable
        base_path = get_base_path()

        certificate_path = os.path.join(base_path, env_vars['AWS_CERTIFICATE_PATH'])
        private_key_path = os.path.join(base_path, env_vars['AWS_PRIVATE_KEY_PATH'])
        aws_signing_helper_path = os.path.join(base_path, env_vars['AWS_SIGNING_HELPER_PATH'])

        # Build the command
        command = [
            aws_signing_helper_path, "credential-process",
            "--certificate", certificate_path,
            "--private-key", private_key_path,
            "--profile-arn", env_vars['AWS_PROFILE_ARN'],
            "--role-arn", env_vars['AWS_ROLE_ARN'],
            "--trust-anchor-arn", env_vars['AWS_TRUST_ANCHOR_ARN']
        ]

        result = subprocess.run(
            command, capture_output=True, text=True, check=True)
        if result.stderr:
            print("Command Error:", result.stderr)

        credentials = json.loads(result.stdout)
        print("AWS Credentials retrieved successfully.")
        return credentials
    except subprocess.CalledProcessError as e:
        print(f"Error fetching AWS credentials: {e.output or e.stderr}")
        return None

# Function to interact with EC2 instances (Start/Stop)
def manage_ec2_instances(action, ec2_client, instances):
    try:
        print(f"Managing EC2 instances: {action}...")
        current_statuses = get_ec2_instance_status(ec2_client, instances)
        
        instances_to_modify = [
            instance_id for instance_id, status in current_statuses.items() 
            if (action == "start" and status['status'] != "running") or 
               (action == "stop" and status['status'] != "stopped")
        ]
        
        if instances_to_modify:
            if action == "start":
                ec2_client.start_instances(InstanceIds=instances_to_modify)
            elif action == "stop":
                ec2_client.stop_instances(InstanceIds=instances_to_modify)
        
        print(f"EC2 instances {action} action completed.")
        return current_statuses
    except Exception as e:
        print(f"Error managing EC2 instances: {e}")
        return {"Error": f"Error managing EC2 instances: {str(e)}"}

# Function to get the status and name of EC2 instances
def get_ec2_instance_status(ec2_client, instances):
    try:
        response = ec2_client.describe_instances(InstanceIds=instances)
        statuses = {}
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                instance_name = "Unnamed"
                if 'Tags' in instance:
                    instance_name = next((tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'), "Unnamed")
                
                statuses[instance_id] = {'name': instance_name, 'status': instance_state}
        return statuses
    except Exception as e:
        print(f"Error fetching EC2 instance status: {e}")
        return {"Error": f"Error fetching instance status: {str(e)}"}

# Function to update the instance status in the UI
def update_instance_status_gui(statuses, instance_status_labels):
    status_color_map = {
        "stopped": "red",
        "pending": "orange",
        "stopping": "orange",
        "running": "green"
    }
    
    for idx, instance in enumerate(statuses.keys()):
        instance_info = statuses.get(instance, {'name': 'Unknown', 'status': 'Unknown'})
        instance_name = instance_info['name']
        instance_status = instance_info['status']
        
        color = status_color_map.get(instance_status, "black")
        
        # Update label's text, color, and font style in one step
        instance_status_labels[idx].config(
            text=f"{instance_name} ({instance}): {instance_status}",
            fg=color,
            font=("Helvetica", 12, "bold")
        )

# Function to check instance status until they are in the required state
def check_instance_status(action, ec2_client, instances, instance_status_labels, status_label, start_button, stop_button):
    global isRunningAction  # Reference the global flag
    last_checked_time = time.time()
    
    while isRunningAction:
        statuses = get_ec2_instance_status(ec2_client, instances)
        
        all_ready = all(
            (action == "start" and status['status'] != "pending") or
            (action == "stop" and status['status'] != "stopping")
            for status in statuses.values()
        )
        
        # If all instances are ready (either started or stopped), break the loop
        if all_ready:
            break

        current_time = time.time()
        # Dynamic status check frequency: every 1 second initially, then every 10 seconds
        if current_time - last_checked_time < 1:
            time.sleep(1)
        else:
            time.sleep(10)
        
        # Update the status on the GUI in each iteration
        update_instance_status_gui(statuses, instance_status_labels)

        last_checked_time = current_time
        
        # Update UI status label with action name and "..."
        status_label.config(text=f"{action.capitalize()}ing EC2 Instances...")

    # One final update of the status after the loop breaks
    statuses = get_ec2_instance_status(ec2_client, instances)  # Fetch final statuses
    update_instance_status_gui(statuses, instance_status_labels)  # Ensure the last instance's status is updated

    # Re-enable buttons and reset the status label
    status_label.after(0, lambda: status_label.config(text="Choose an action."))
    status_label.after(0, lambda: start_button.config(state=tk.NORMAL))
    status_label.after(0, lambda: stop_button.config(state=tk.NORMAL))

    # Reset the global action status
    isRunningAction = False

# Function to handle EC2 instance start action
def on_start(ec2_client, instances, start_button, stop_button, instance_status_labels, status_label):
    global isRunningAction  # Reference the global flag
    
    if isRunningAction:
        return  # If an action is already running, don't start another
    
    print("Starting instances...")
    
    # Set the flag that an action is in progress
    isRunningAction = True
    
    # Disable both buttons while action is processing
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.DISABLED)

    statuses = manage_ec2_instances("start", ec2_client, instances)
    
    # Run status check in a background thread to avoid UI blocking
    threading.Thread(target=check_instance_status, args=("start", ec2_client, instances, instance_status_labels, status_label, start_button, stop_button), daemon=True).start()

    update_instance_status_gui(statuses, instance_status_labels)

# Function to handle EC2 instance stop action
def on_stop(ec2_client, instances, start_button, stop_button, instance_status_labels, status_label):
    global isRunningAction  # Reference the global flag
    
    if isRunningAction:
        return  # If an action is already running, don't stop another
    
    print("Stopping instances...")
    
    # Set the flag that an action is in progress
    isRunningAction = True
    
    # Disable both buttons while action is processing
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.DISABLED)

    statuses = manage_ec2_instances("stop", ec2_client, instances)
    
    # Run status check in a background thread to avoid UI blocking
    threading.Thread(target=check_instance_status, args=("stop", ec2_client, instances, instance_status_labels, status_label, start_button, stop_button), daemon=True).start()

    update_instance_status_gui(statuses, instance_status_labels)

# Function to create and manage the GUI
def create_gui(ec2_client, instances):
    window = tk.Tk()
    window.title("EC2 Instance Manager")

    start_button = tk.Button(window, text="Start Instances", command=lambda: on_start(ec2_client, instances, start_button, stop_button, instance_status_labels, status_label))
    start_button.grid(row=0, column=0, padx=10, pady=10)

    stop_button = tk.Button(window, text="Stop Instances", command=lambda: on_stop(ec2_client, instances, start_button, stop_button, instance_status_labels, status_label))
    stop_button.grid(row=1, column=0, padx=10, pady=10)

    status_label = tk.Label(window, text="Choose an action.", width=40)
    status_label.grid(row=2, column=0, pady=10)

    instance_status_labels = []
    for idx, instance in enumerate(instances):
        instance_status_labels.append(tk.Label(window, text=f"Instance {instance}:", width=40))
        instance_status_labels[-1].grid(row=3 + idx, column=0, pady=5)

    # Fetch initial statuses when GUI starts and update the labels
    initial_statuses = get_ec2_instance_status(ec2_client, instances)
    update_instance_status_gui(initial_statuses, instance_status_labels)

    window.mainloop()

# Main function to fetch AWS credentials and create GUI
def main():
    credentials = get_aws_credentials()
    if credentials:
        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"]
        )
        
        ec2_client = session.client("ec2", region_name="eu-central-1")
        instances = env_vars['AWS_INSTANCE_IDS'].split(',')

        create_gui(ec2_client, instances)

if __name__ == "__main__":
    main()
