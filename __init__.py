# __init__.py
# This package contains utilities for the project
import os
import sys


# Get the current directory of the __init__.py file
current_dir = os.path.dirname(__file__)

# Add the current directory to the system path
sys.path.append(current_dir)