import sys

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_step(step_num, total_steps, description):
    print(f"\n{Colors.BLUE}[{step_num}/{total_steps}]{Colors.END} {Colors.BOLD}{description}{Colors.END}")

def print_success(message):
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")

def print_error(message):
    print(f"  {Colors.RED}✗{Colors.END} {message}")

def print_info(message):
    print(f"  {Colors.YELLOW}ℹ{Colors.END} {message}")

def exit_on_error(message):
    print_error(f"Deployment failed: {message}")
    print(f"\n{Colors.RED}Deployment terminated due to error.{Colors.END}")
    sys.exit(1)


def load_config():
    import json
    try:
        with open('./config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Please run 'python deploy.py' first.")
        exit(1)