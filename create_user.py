#!/usr/bin/env python
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.AuthManager import AuthManager

def main():
    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    auth_manager = AuthManager()
    
    if auth_manager.create_user(username, password):
        print(f"User '{username}' created successfully.")
    else:
        print(f"Failed to create user '{username}'. Username may already exist.")

if __name__ == "__main__":
    main() 