# AWS EC2 Start/Stop Automation

This project automates the process of starting and stopping EC2 instances on AWS account from anywhere while displaying real time status.


![image](https://github.com/user-attachments/assets/8d047499-e308-4086-9f03-1b20a0d8bd15)


## Prerequisites

Ensure you have completed the following steps:

1. **Create AWS Policy, Role, and Roles Anywhere Setup (Trust Anchor & Profile) and attach them all**
2. **Download AWS Signing Helper (If file in repository doesnt work/old)**
3. **SmallStep CLI for Certificate & Keys Generation**
4. **Python Script Execution & Packaging with PyInstaller**

---

## 1. AWS Policy, Role, Roles Anywhere Anchor & Profile ☁️

### Create IAM Policy, Role & Roles Anywhere

1. **Create a Custom IAM Policy** for EC2 permissions (e.g., to start/stop instances). Example policy: 📄
   ```json
   {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ec2:Describe*",
                "ec2:StartInstances",
                "ec2:StopInstances",
                "kms:CreateGrant"
            ],
            "Resource": "*"
        }
    ]
   }
2. **Create Role** for the Roles Anywhere feature with Assume Role trust actions.Example trust policy: 📃
   ```json
   {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "rolesanywhere.amazonaws.com"
            },
            "Action": [
                "sts:AssumeRole",
                "sts:TagSession",
                "sts:SetSourceIdentity"
            ],
            "Condition": {
                "ArnEquals": {
                    "aws:SourceArn": "arn:aws:rolesanywhere:{REGION}:{ACCOUNT_ID}:trust-anchor/{TRUST_ANCHOR_ID}"
                }
            }
        }
    ]
   }
3. **Create Roles Anywhere Profile**, attach the created role and policy. 📖
4. **Create Roles Anywhere Trust anchor** with pasting the main Certificate (create with step cli on next section). 📑

## 2. Create Certificate & Keys using step cli : 🦿

### Open terminal in step bin directory where step.exe exsits and execute the following:

1. CREATE MAIN CRT & KEY
   ```bash
   step certificate create "{NAME_INPUT}" {NAME_INPUT}.crt {NAME_INPUT}.key --profile root-ca
   ```
2. CREATE CLIENT SIDE (leaf)
   ```bash
   step certificate create "{NAME_INPUT} client" {NAME_INPUT}-client.crt {NAME_INPUT}-client.key --profile leaf --ca ./{NAME_INPUT}.crt --ca-key ./{NAME_INPUT}.key --not-after {HOURS_TO_EXPIRE}h
   ```
4. REMOVE PASS ON CLIENT KEY
   ```bash
   step crypto change-pass ./{NAME_INPUT}-client.key
   ```
5. CHECK VALIDITY
   ```bash
   step certificate inspect ExternalEC2StartStop-client.crt
   ```

### TEST Run the following command which should output AWS cred for the role we created :
```bash
aws_signing_helper credential-process --certificate ./{NAME_INPUT}-client.crt --private-key ./{NAME_INPUT}-client.key --profile-arn arn:aws:rolesanywhere:{REGION}:{ACCOUNT_ID}:profile/{PROFILE_ID} --role-arn arn:aws:iam::{ACCOUNT_ID}:role/ExternalStartStopEC2 --trust-anchor-arn arn:aws:rolesanywhere:{REGION}:{ACCOUNT_ID}:trust-anchor/{TRUST_ANCHOR_ID}
```

## 3. Python Script Execution & Packaging with PyInstaller 🗃️

After setting up the AWS roles and certificates, follow these steps to execute and package the Python script:

1.    **Update Relevant Data In The Main Script**<br />

      a. Update Relevant AMIs in the instances list<br />
      b. Update AWS Cred Command With All needed data like the AWS cred TEST Run<br />
  
3.    **Install Required Python Packages**

   - Install the necessary Python packages listed in `requirements.txt` by running:
     ```bash
     pip install -r requirements.txt
     ```

3. **Run the Python Script**

   - Execute the main Python script to verify it starts/stops EC2 instances correctly:
     ```bash
     python main.py
     ```

4. **Package the Script with PyInstaller**

   - Package the Python script as a standalone executable using PyInstaller.
   - If PyInstaller is not installed, install it first:
     ```bash
     pip install pyinstaller
     ```

   - Then, build the executable:
     ```bash
     pyinstaller --onefile --windowed --add-data "{NAME_INPUT}-client.crt;." --add-data "{NAME_INPUT}-client.key;." --add-binary "aws_signing_helper.exe;." {NAME_INPUT}.py
     ```

   - This will create an executable in the `dist` folder. You can distribute this executable to run the automation without requiring Python to be installed on the target machine.

5. **Run the Packaged Executable**

   - Test the packaged executable to ensure it functions correctly:
     ```bash
     ./dist/main
     ```
     
### Troubleshooting: PyInstaller Command Not Found

If you encounter an error indicating that `pyinstaller` cannot be found, you may need to add the Python Scripts directory to your system’s PATH environment variable. Here’s how to do it:

1. **Find the Python Scripts Path**

   - Run the following command in your terminal to find the location of installed Python scripts:
     ```bash
     pip show pip
     ```
   - Look for the line starting with `Location:`. The `Scripts` folder inside this path is where `pyinstaller` (and other tools installed via pip) are typically located. 
   - For example, if the location is `C:\Users\YourUserName\AppData\Local\Programs\Python\Python39`, then the Scripts path would be:
     ```
     C:\Users\YourUserName\AppData\Local\Programs\Python\PythonXYZ\Scripts
     ```

2. **Add the Python Scripts Path to the PATH Environment Variable**

   - **On Windows**:
     1. Press `Win + R` to open the Run dialog.
     2. Type `sysdm.cpl` and press **Enter** to open System Properties.
     3. Go to the **Advanced** tab and click on **Environment Variables**.
     4. In the **System variables** section, find and select the `Path` variable, then click **Edit** and add the path.
     5. Click **OK** to save and close all dialog boxes.

   - **On macOS/Linux**:
     1. Open your terminal.
     2. Add the Scripts directory to the PATH by appending this line to your shell configuration file (e.g., `~/.bashrc`, `~/.zshrc`):
        ```bash
        export PATH="$PATH:/path/to/your/python/scripts"
        ```
     3. Save the file and reload the configuration by running:
        ```bash
        source ~/.bashrc  # or ~/.zshrc if using zsh
        ```

3. **Verify PyInstaller Installation**

   - After updating the PATH, verify that `pyinstaller` is accessible by running:
     ```bash
     pyinstaller --version
     ```
   - If the version number is displayed, you are ready to package the script as described in the previous section.

This should resolve the issue with PyInstaller not being found.
