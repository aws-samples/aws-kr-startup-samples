#!/bin/bash

# AI-DLC Skill Installer
# This script installs the AI-DLC skill for Claude Code

set -e

REPO_URL="https://github.com/awslabs/aidlc-workflows.git"
SKILL_DIR_NAME="aidlc"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         AI-DLC (AI-Driven Development Life Cycle)            ║"
echo "║                    Skill Installer                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to check if git is installed
check_git() {
    if ! command -v git &> /dev/null; then
        echo -e "${RED}Error: git is not installed. Please install git first.${NC}"
        exit 1
    fi
}

# Function to create directory if it doesn't exist
create_dir() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}Created directory: $dir${NC}"
    fi
}

# Function to install skill
install_skill() {
    local base_path=$1
    local skill_path="${base_path}/skills/${SKILL_DIR_NAME}"
    local workflows_path="${skill_path}/aidlc-workflows"

    echo -e "${YELLOW}Installing to: ${skill_path}${NC}"

    # Create skill directory
    create_dir "$skill_path"

    # Clone or update repository
    if [ -d "$workflows_path" ]; then
        echo -e "${YELLOW}Repository already exists. Updating...${NC}"
        cd "$workflows_path"
        git pull origin main
        cd - > /dev/null
    else
        echo -e "${YELLOW}Cloning repository...${NC}"
        git clone "$REPO_URL" "$workflows_path"
    fi

    # Copy SKILL.md to skill directory
    local skill_md_source="${workflows_path}/SKILL.md"
    local skill_md_dest="${skill_path}/SKILL.md"

    if [ -f "$skill_md_source" ]; then
        cp "$skill_md_source" "$skill_md_dest"
        echo -e "${GREEN}SKILL.md copied to: ${skill_md_dest}${NC}"
    else
        echo -e "${RED}Warning: SKILL.md not found in cloned repository${NC}"
    fi

    echo ""
    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo -e "${BLUE}Skill installed at: ${skill_path}${NC}"
}

# Main menu
echo "Where would you like to install the AI-DLC skill?"
echo ""
echo "  1) Global installation (~/.claude/skills/aidlc)"
echo "     - Available across all projects"
echo ""
echo "  2) Local installation (./.claude/skills/aidlc)"
echo "     - Only available in current project"
echo ""
read -p "Enter your choice (1 or 2): " choice

check_git

case $choice in
    1)
        echo ""
        echo -e "${BLUE}Installing globally...${NC}"
        install_skill "$HOME/.claude"
        echo ""
        echo -e "${YELLOW}Note: Global skills are available in all your Claude Code projects.${NC}"
        ;;
    2)
        echo ""
        echo -e "${BLUE}Installing locally...${NC}"
        install_skill "./.claude"
        echo ""
        echo -e "${YELLOW}Note: Local skills are only available in this project directory.${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice. Please run the script again and select 1 or 2.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Installation Complete!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "To use AI-DLC, run Claude Code and type:"
echo -e "  ${BLUE}/aidlc [your task description]${NC}"
echo ""
