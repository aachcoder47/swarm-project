#!/usr/bin/env bash
# =============================================================
# FrontierX Scout — Environment Setup Script
# =============================================================
# Installs all dependencies on Ubuntu 22.04 for ROS 2 Humble
# development of the FrontierX Scout robotics platform.
#
# Usage:
#   chmod +x scripts/setup.sh
#   ./scripts/setup.sh
# =============================================================

set -euo pipefail

FRONTIERX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO="humble"
PYTHON_VERSION="3.10"

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║   FrontierX Labs — Environment Setup       ║"
echo "║   Ubuntu 22.04 + ROS 2 Humble              ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# ── Check OS ──────────────────────────────────────────────────
if [[ "$(lsb_release -si 2>/dev/null)" != "Ubuntu" ]]; then
  echo "WARNING: This script is designed for Ubuntu 22.04."
  echo "         Current OS: $(uname -s). Proceeding anyway..."
fi

# ── Check root / sudo ─────────────────────────────────────────
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo &>/dev/null; then
    SUDO="sudo"
  else
    echo "ERROR: This script must be run as root or with sudo installed."
    exit 1
  fi
fi

# ── Package Manager Detection ───────────────────────────────
if ! command -v apt-get &>/dev/null; then
  echo ""
  echo "⚠️  'apt-get' package manager not found on this Linux environment."
  echo "    ROS 2 Humble binaries are natively packaged for Ubuntu 22.04 LTS (Debian/apt)."
  echo ""
  echo "💡 Recommended solutions:"
  echo "   1. Run via Docker Compose (works on any Linux distro & Windows):"
  echo "      docker compose -f docker/docker-compose.yml up --build"
  echo ""
  echo "   2. If using WSL2, ensure your distro is Ubuntu 22.04 LTS:"
  echo "      wsl -d Ubuntu-22.04"
  echo ""
  exit 1
fi

# ── Update system ─────────────────────────────────────────────
echo "[1/8] Updating system packages..."
$SUDO apt-get update -q
$SUDO apt-get upgrade -y -q

# ── Install ROS 2 Humble ──────────────────────────────────────
echo "[2/8] Installing ROS 2 Humble..."
if ! command -v ros2 &>/dev/null; then
  $SUDO apt-get install -y software-properties-common
  $SUDO add-apt-repository -y universe
  $SUDO apt-get update -q
  $SUDO apt-get install -y curl
  $SUDO curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | \
    $SUDO apt-key add -
  $SUDO sh -c 'echo "deb [arch=$(dpkg --print-architecture)] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/ros2-latest.list'
  $SUDO apt-get update -q
  $SUDO apt-get install -y ros-${ROS_DISTRO}-desktop-full
  echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
else
  echo "  ROS 2 already installed."
fi

# ── Install ROS 2 Navigation Stack ────────────────────────────
echo "[3/8] Installing Nav2, SLAM Toolbox, robot_localization..."
$SUDO apt-get install -y \
  ros-${ROS_DISTRO}-navigation2 \
  ros-${ROS_DISTRO}-nav2-bringup \
  ros-${ROS_DISTRO}-slam-toolbox \
  ros-${ROS_DISTRO}-robot-localization \
  ros-${ROS_DISTRO}-ros2-control \
  ros-${ROS_DISTRO}-ros2-controllers \
  ros-${ROS_DISTRO}-diff-drive-controller \
  ros-${ROS_DISTRO}-twist-mux \
  ros-${ROS_DISTRO}-teleop-twist-keyboard \
  ros-${ROS_DISTRO}-robot-state-publisher \
  ros-${ROS_DISTRO}-joint-state-publisher \
  ros-${ROS_DISTRO}-joint-state-publisher-gui \
  ros-${ROS_DISTRO}-xacro \
  ros-${ROS_DISTRO}-foxglove-bridge \
  ros-${ROS_DISTRO}-rviz2 \
  ros-${ROS_DISTRO}-diagnostic-updater \
  ros-${ROS_DISTRO}-tf2-tools \
  ros-${ROS_DISTRO}-cv-bridge \
  ros-${ROS_DISTRO}-image-transport \
  ros-${ROS_DISTRO}-nav2-map-server

# ── Install build tools ───────────────────────────────────────
echo "[4/8] Installing build tools..."
$SUDO apt-get install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  python3-pip \
  cmake \
  build-essential \
  git \
  wget \
  htop \
  tmux

# Initialize rosdep
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  $SUDO rosdep init
fi
rosdep update

# ── Install Python dependencies ───────────────────────────────
echo "[5/8] Installing Python dependencies..."
pip3 install --user --no-cache-dir \
  ultralytics \
  opencv-python \
  torch \
  torchvision \
  ollama \
  pydantic \
  jsonschema \
  numpy \
  scipy \
  psutil \
  pyyaml \
  click \
  rich \
  loguru \
  pytest \
  pytest-cov

# ── Install Docker ────────────────────────────────────────────
echo "[6/8] Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  if command -v sudo &>/dev/null; then
    sudo usermod -aG docker "$USER" 2>/dev/null || true
  fi
  echo "  Docker installed."
else
  echo "  Docker already installed."
fi

# ── Install NVIDIA Container Toolkit ─────────────────────────
echo "[7/8] Installing NVIDIA Container Toolkit (if GPU present)..."
if command -v nvidia-smi &>/dev/null; then
  distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    $SUDO gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    $SUDO tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
  $SUDO apt-get update -q
  $SUDO apt-get install -y nvidia-container-toolkit
  $SUDO nvidia-ctk runtime configure --runtime=docker
  $SUDO systemctl restart docker 2>/dev/null || true
else
  echo "  No NVIDIA GPU detected. Skipping container toolkit."
fi

# ── Install ollama ────────────────────────────────────────────
echo "[8/8] Installing ollama (local LLM server)..."
if ! command -v ollama &>/dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh
  echo "  ollama installed."
  echo "  To pull the LLM: ollama pull llama3.1:8b"
else
  echo "  ollama already installed."
fi

# ── Setup ROS 2 workspace ─────────────────────────────────────
echo ""
echo "Setting up ROS 2 workspace at: ${FRONTIERX_ROOT}"
cd "${FRONTIERX_ROOT}"

# Add workspace source to bashrc
if ! grep -q "frontierx" ~/.bashrc; then
  cat >> ~/.bashrc << EOF

# FrontierX Robotics workspace
source /opt/ros/${ROS_DISTRO}/setup.bash
source ${FRONTIERX_ROOT}/install/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
alias frontierx_build='cd ${FRONTIERX_ROOT} && colcon build --symlink-install'
alias frontierx_sim='${FRONTIERX_ROOT}/scripts/launch_sim.sh'
EOF
fi

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║   Setup complete!                          ║"
echo "║                                            ║"
echo "║   Next steps:                              ║"
echo "║   1. source ~/.bashrc                      ║"
echo "║   2. ./scripts/build.sh                   ║"
echo "║   3. Open dashboard/index.html in browser  ║"
echo "║   4. Install Isaac Sim (requires NVIDIA)   ║"
echo "╚════════════════════════════════════════════╝"
