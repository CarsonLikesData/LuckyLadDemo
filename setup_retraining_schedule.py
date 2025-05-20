"""
Setup Document AI Retraining Schedule
------------------------------------
This script helps set up a scheduled task to run the Document AI retraining process
automatically. It creates a scheduled task on Windows or a cron job on Linux/Mac.

Usage:
    python setup_retraining_schedule.py
"""

import os
import sys
import platform
import subprocess
import argparse
from datetime import datetime

def setup_windows_task(python_path, script_path, schedule_time, task_name):
    """Set up a scheduled task on Windows"""
    print(f"Setting up Windows scheduled task '{task_name}'...")
    
    # Create the XML file for the task
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}</Date>
    <Author>Document AI Retraining Setup</Author>
    <Description>Automatically retrain Document AI with corrected invoices</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{datetime.now().strftime('%Y-%m-%dT')}{{schedule_time}}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>{script_path}</Arguments>
      <WorkingDirectory>{os.path.dirname(script_path)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
    
    # Save the XML file
    xml_path = os.path.join(os.path.dirname(script_path), "document_ai_retraining_task.xml")
    with open(xml_path, "w") as f:
        f.write(xml_content)
    
    # Create the task using schtasks
    cmd = f'schtasks /create /tn "{task_name}" /xml "{xml_path}" /f'
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"Successfully created scheduled task '{task_name}'")
        print(f"The task will run daily at {schedule_time}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating scheduled task: {e}")
        print("You may need to run this script as administrator")
    
    # Clean up the XML file
    try:
        os.remove(xml_path)
    except:
        pass

def setup_linux_cron(python_path, script_path, schedule_time, log_path):
    """Set up a cron job on Linux/Mac"""
    print("Setting up Linux/Mac cron job...")
    
    # Parse the schedule time
    hour, minute = schedule_time.split(":")
    
    # Create the cron entry
    cron_entry = f"{minute} {hour} * * * {python_path} {script_path} >> {log_path} 2>&1\n"
    
    # Create a temporary file with the current crontab
    try:
        subprocess.run("crontab -l > temp_crontab", shell=True)
    except:
        # If no crontab exists, create an empty file
        with open("temp_crontab", "w") as f:
            f.write("")
    
    # Check if the entry already exists
    with open("temp_crontab", "r") as f:
        current_crontab = f.read()
    
    if script_path in current_crontab:
        print("A cron job for this script already exists. Updating it...")
        # Remove the existing entry
        new_crontab = []
        for line in current_crontab.splitlines():
            if script_path not in line:
                new_crontab.append(line)
        current_crontab = "\n".join(new_crontab) + "\n"
    
    # Add the new entry
    with open("temp_crontab", "w") as f:
        f.write(current_crontab + cron_entry)
    
    # Install the new crontab
    try:
        subprocess.run("crontab temp_crontab", shell=True, check=True)
        print(f"Successfully created cron job")
        print(f"The job will run daily at {schedule_time}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating cron job: {e}")
    
    # Clean up the temporary file
    try:
        os.remove("temp_crontab")
    except:
        pass

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Set up a scheduled task for Document AI retraining")
    parser.add_argument("--time", default="02:00", help="Time to run the task (24-hour format, e.g., 02:00)")
    parser.add_argument("--python", default=sys.executable, help="Path to Python executable")
    parser.add_argument("--script", default="auto_retrain_document_ai.py", 
                        help="Path to the retraining script (default: auto_retrain_document_ai.py)")
    parser.add_argument("--log", default="document_ai_retraining.log", 
                        help="Path to log file (for Linux/Mac)")
    parser.add_argument("--task-name", default="DocumentAIRetraining", 
                        help="Name of the scheduled task (for Windows)")
    
    args = parser.parse_args()
    
    # Get absolute paths
    script_path = os.path.abspath(args.script)
    log_path = os.path.abspath(args.log)
    
    # Check if the script exists
    if not os.path.exists(script_path):
        print(f"Error: Script not found at {script_path}")
        return
    
    # Set up the scheduled task based on the platform
    system = platform.system()
    if system == "Windows":
        setup_windows_task(args.python, script_path, args.time, args.task_name)
    elif system in ["Linux", "Darwin"]:  # Linux or Mac
        setup_linux_cron(args.python, script_path, args.time, log_path)
    else:
        print(f"Unsupported platform: {system}")
        print("Please set up the scheduled task manually.")

if __name__ == "__main__":
    main()