# RAM Monitor Desktop Widget

A lightweight Windows desktop-layer widget. It is attached to the Windows desktop WorkerW surface, so it stays on the wallpaper layer behind normal application windows instead of floating above them.

## Build
GitHub Actions builds a portable Windows x64 executable:
1. Open **Actions**.
2. Select **Build RAM Monitor Desktop Widget**.
3. Run the workflow.
4. Download the **RAMMonitor-Desktop-Widget-Windows-x64** artifact.

No Python installation is needed on the target PC.

## Features
- RAM used, total RAM, and available RAM
- CPU usage
- Compact translucent desktop display
- Updates every 2 seconds
- Right-click menu to refresh or exit

The widget is positioned at the top-left desktop area by default. Change X and Y near the top of `ram_monitor_desktop.py` to reposition it.
