#!/usr/bin/env python3
"""
Environment testing script for YouTube Shorts Uploader
"""

import sys
import os
import platform
import pkg_resources
import importlib.util
import subprocess

def print_section(title):
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

print_section("SYSTEM INFORMATION")
print(f"Python Version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Architecture: {platform.architecture()}")
print(f"Machine: {platform.machine()}")
print(f"Node: {platform.node()}")
print(f"System: {platform.system()}")

print_section("ENVIRONMENT VARIABLES")
for key, value in os.environ.items():
    if "PATH" in key or "PYTHON" in key or "QT" in key:
        print(f"{key}: {value}")

print_section("INSTALLED PACKAGES")
installed_packages = sorted([f"{d.project_name}=={d.version}" 
                           for d in pkg_resources.working_set])
for package in installed_packages:
    if any(x in package.lower() for x in ["pyqt", "qt", "pyside", "opencv", "google", "openai"]):
        print(package)

print_section("PYQT DETAILS")
print("Checking PyQt6 installation...")

# Check if PyQt6 module is available
pyqt6_spec = importlib.util.find_spec("PyQt6")
if pyqt6_spec:
    print(f"PyQt6 found at: {pyqt6_spec.origin}")
    print(f"PyQt6 submodule path: {pyqt6_spec.submodule_search_locations}")
    
    # List all files in the PyQt6 directory
    pyqt_dir = os.path.dirname(pyqt6_spec.origin)
    print(f"\nFiles in PyQt6 directory ({pyqt_dir}):")
    try:
        for i, file in enumerate(sorted(os.listdir(pyqt_dir))):
            print(f"  - {file}")
            if i > 20:  # Limit to 20 files
                print("  ... (more files)")
                break
    except Exception as e:
        print(f"  Error listing files: {e}")
    
    # Try importing QtCore
    print("\nTrying to import QtCore...")
    try:
        from PyQt6 import QtCore
        print(f"  Successfully imported QtCore")
        print(f"  Qt version: {QtCore.QT_VERSION_STR}")
    except ImportError as e:
        print(f"  Failed to import QtCore: {e}")
        
        # Check if the file exists
        qtcore_path = os.path.join(pyqt_dir, "QtCore.abi3.so")
        if os.path.exists(qtcore_path):
            print(f"  QtCore.abi3.so exists at: {qtcore_path}")
        else:
            print(f"  QtCore.abi3.so does not exist")
            
            # Search for QtCore files
            print("  Searching for QtCore files...")
            try:
                result = subprocess.run(["find", pyqt_dir, "-name", "*QtCore*"], 
                                      capture_output=True, text=True)
                if result.stdout:
                    for line in result.stdout.splitlines():
                        print(f"    Found: {line}")
                else:
                    print("    No QtCore files found")
            except Exception as e:
                print(f"    Error searching for QtCore: {e}")
            
    # Try importing QtMultimedia
    print("\nTrying to import QtMultimedia...")
    try:
        from PyQt6 import QtMultimedia
        print("  Successfully imported QtMultimedia")
        print(f"  Available QtMultimedia classes: {dir(QtMultimedia)[:5]}...")
    except ImportError as e:
        print(f"  Failed to import QtMultimedia: {e}")
        
else:
    print("PyQt6 module not found in sys.path")
    print(f"sys.path: {sys.path}")

print_section("PIP CHECK")
try:
    result = subprocess.run(["pip", "check"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
except Exception as e:
    print(f"Error running pip check: {e}")

if __name__ == "__main__":
    print_section("SCRIPT PATHS")
    print(f"Script Directory: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Python Path: {sys.path}") 