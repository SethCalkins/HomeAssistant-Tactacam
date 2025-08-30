"""Constants for the Reveal Cell Cam integration."""

DOMAIN = "reveal_cell_cam"

API_BASE_URL = "https://api.reveal.ishareit.net"
API_VERSION = "v1"

USER_AGENT = "RevealWeb/5.4.0"

DEFAULT_SCAN_INTERVAL = 300  # 5 minutes in seconds

# Hardware version to model name mapping
HARDWARE_MODEL_MAP = {
    "R8.0": "Reveal Pro 3.0",
    "R7.0": "Reveal X Pro 3.0", 
    "R6.0": "Reveal X Pro",
    "R5.0": "Reveal X",
    "R4.0": "Reveal SK",
    # Add more mappings as discovered
}