# BPFDoor Malware Inspection Guide

The Korea Internet & Security Agency (KISA) provides guidance on how to inspect for the backdoor malware 'BPFDoor' related to recent hacking incidents.

This guide is available on the Boho-nara security notice board. Please refer to the inspection guide distributed by KISA to conduct system inspections.

## What is BPFDoor Malware?

According to the KISA BPFDoor inspection guide, BPFDoor is an advanced malware targeting Linux operating systems. This malware exploits the Berkeley Packet Filter (BPF) functionality of the Linux kernel to maintain persistent access to systems. It has strong persistence and stealth capabilities, making detection and removal extremely difficult.

## Response Measures

The following response measures are recommended:
- Apply latest kernel patches and security updates
- Restrict BPF usage
- Enhance log monitoring
- Utilize host-based IPS/IDS
- Analyze network traffic

## Inspection Tools

The `bpfdoor_bpf.sh` and `bpfdoor_env.sh` provided in the guide are shell script tools for automatically checking BPFDoor infection status.

### bpfdoor_bpf.sh
This script inspects BPF (Berkeley Packet Filter) filters registered in the system. It automates commands like `ss -0pb` to analyze BPF filter information that is difficult to check manually and identifies traces of malware.

### bpfdoor_env.sh
This script inspects environment variables of processes running on the system. It identifies processes using suspicious environment variables to determine potential infection:
- `HOME=/tmp` (setting home directory to temporary folder)
- `HISTFILE=/dev/null` (setting to not record command history)

Through these two scripts, system administrators can easily inspect the main characteristics of BPFDoor malware - 'BPF filter usage' and 'specific environment variable settings' - without directly entering complex commands.

## Inspecting BPFDoor on Amazon EC2

To inspect BPFDoor malware using these scripts on Amazon EC2 instances, you can utilize AWS Systems Manager.

Using Systems Manager's Run Command feature allows you to automate inspection tasks, and you can use Amazon Q Developer CLI to perform tasks, aggregate results, and generate reports.

### Prerequisites

**Amazon Q Developer CLI Setup:**
1. Install Amazon Q Developer CLI.
2. Complete authentication with Builder ID or IAM account.

**EC2 Instance Requirements:**
- SSM Agent must be installed.
- An IAM instance profile with permissions to communicate with AWS Systems Manager service must be attached.
- SSM Agent must be able to communicate with AWS Systems Manager endpoints via HTTPS (port 443).

**AWS CLI Account Permissions:**
- Permissions to execute AWS Systems Manager Run Command are required.

### Execution Method

1. **Register Context**
   Run Amazon Q Developer CLI and register the following files as context:
   - `bpfdoor_bpf.sh`
   - `bpfdoor_env.sh`
   - `bpfdoor_inspection_template.html` (report template)

   ```
   /context add <paths...>
   ```

2. **Execute Inspection**
   Enter a prompt like the following:

   **Prompt Example:**
   ```
   Connect directly to EC2 instances running in the ap-northeast-2 region using AWS Systems Manager Run Command feature, check for BPFDoor malware using bpfdoor_env.sh and bpfdoor_bpf.sh scripts, and generate a report in bpfdoor_inspection_template.html format.
   ```

   > **Tip:** Clearly specifying targets can reduce Q Developer CLI execution time.

3. **Check Results**
   Once inspection is complete, you can review the results through the generated report.

Through this method, you can efficiently perform BPFDoor malware inspection across multiple EC2 instances and obtain systematic security inspection results. 

The example above is a good case for applying the Amazon Q Developer CLI to your operations. However, please note that due to the nature of AI-generated responses, the content may not always be completely accurate. It’s best to use this information as a reference and verify it before applying it to any critical tasks.