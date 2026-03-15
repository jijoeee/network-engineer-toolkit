# 🌐 Network Engineer Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![UI: customtkinter](https://img.shields.io/badge/UI-customtkinter-blueviolet)](https://github.com/TomSchimansky/CustomTkinter)

An extensible Python suite for network automation and engineering. Built for reliability, speed, and enterprise workflows.

## 🧰 Tools Included

| Tool | Status | Description |
|------|--------|-------------|
| **IP Subnet Calculator** | ✅ Active | High-performance IPv4/IPv6 subnetting, VLSM calculation, and smart next-hop logic with a modern Dark Mode GUI. |
| **Bulk Network Ping Monitor** | ✅ Active | High-speed, parallel ping monitoring for hundreds of devices with a live dark-mode dashboard, Excel integration, and automated CSV reporting. |
... In progress ...

## 🚀 Installation & Setup

1. Clone the repository to your local machine:
```bash
git clone [https://github.com/jijoeee/network-engineer-toolkit.git](https://github.com/jijoeee/network-engineer-toolkit.git)
cd network-engineer-toolkit
```
Install the required GUI dependencies:

```Bash

pip install -r requirements.txt
```
2. Navigate to the tool's directory and launch the GUI:

```Bash

cd tools/subnet_calculator
python ip_subnet_calculator.py
```

## ✨ Current Features

1) IP Subnet Calculator

    IPv4 & IPv6 Support: Handles both protocols seamlessly using Python's native ipaddress library.
    
    Smart Next-Hop Logic: Accurately calculates next-hops, specifically accounting for /31 and /127 point-to-point links.
    
    Subnet Splitting Engine: Slice large blocks (e.g., /24) into smaller prefixes (e.g., /28) using a low-memory generator algorithm.
    
    Modern Interface: Built with customtkinter for a professional, dark-mode-first user experience.

2) Bulk Network Ping Monitor
    
    Parallel Execution Engine: Uses Python's ThreadPoolExecutor to simultaneously ping hundreds of devices, dropping scan times from minutes to seconds.
    
    Smart Excel Integration: Directly imports device inventory (Hostname, IP, Location, Type, Group) from devices.xlsx without rigid header requirements.
    
    Advanced Analytics Tracking: Continuously tracks and calculates Packet Loss %, Uptime, Last Down Time, and Total Ping Counts per session.
    
    Dynamic Smart Filtering: Instantly filter the live dashboard by Device Group, Location, Type, or UP/DOWN status.
    
    Session Management: Features a clean Pause/Resume engine and automatically resets data counters upon starting a fresh session.
    
    Automated NOC Reporting: One-click export dynamically generates a timestamped CSV report and saves it directly to a dedicated report/ directory.
