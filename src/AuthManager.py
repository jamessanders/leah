import json
import os
import hashlib
import secrets
import time
from pathlib import Path
from typing import Dict, Any, Optional
from LocalConfigManager import LocalConfigManager

class AuthManager:
    def __init__(self):
        """
        Initialize the AuthManager with a user ID.
        
        Args:
            user_id (str): The user ID to create a config directory for
        """
        self.config_manager = LocalConfigManager("auth")
        self.config_path = self.config_manager.get_path("auth.json")
        self.auth_data: Dict[str, Any] = {}
        self.load_auth_data()
        # Token expiration time in seconds (1 year)
        self.token_expiration = 86400*365

    def load_auth_data(self) -> None:
        """
        Load authentication data from the auth.json file.
        Creates the file if it doesn't exist.
        """
        if not os.path.exists(self.config_path):
            # Create an empty auth.json file with a basic structure
            default_auth = {
                "users": {}
            }
            with open(self.config_path, 'w') as f:
                json.dump(default_auth, f, indent=4)
        
        try:
            with open(self.config_path, 'r') as f:
                self.auth_data = json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in {self.config_path}")
        except Exception as e:
            raise Exception(f"Error loading auth data: {str(e)}")

    def create_user(self, username: str, password: str) -> bool:
        """
        Create a new user with a hashed password.
        
        Args:
            username (str): The username for the new user
            password (str): The plain text password to hash and store
            
        Returns:
            bool: True if user was created successfully, False if username already exists
        """
        if username in self.auth_data["users"]:
            return False
            
        # Generate a random salt
        salt = secrets.token_hex(16)
        
        # Hash the password with the salt
        hashed_password = hashlib.md5((password + salt).encode()).hexdigest()
        
        # Store the user data
        self.auth_data["users"][username] = {
            "password_hash": hashed_password,
            "salt": salt,
            "tokens": {}
        }
        
        # Save the updated auth data
        self.update_auth_data(self.auth_data)
        return True

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate a user and generate a token.
        
        Args:
            username (str): The username to authenticate
            password (str): The password to verify
            
        Returns:
            Optional[str]: The authentication token if successful, None if authentication failed
        """
        if username not in self.auth_data["users"]:
            return None
            
        user_data = self.auth_data["users"][username]
        salt = user_data["salt"]
        
        # Hash the provided password with the stored salt
        hashed_password = hashlib.md5((password + salt).encode()).hexdigest()
        
        # Verify the password
        if hashed_password != user_data["password_hash"]:
            return None
            
        # Generate a new token
        token = secrets.token_urlsafe(32)
        expiration = int(time.time()) + self.token_expiration
        
        # Store the token with its expiration
        if "tokens" not in user_data:
            user_data["tokens"] = {}
            
        user_data["tokens"][token] = {
            "created_at": int(time.time()),
            "expires_at": expiration
        }
        
        # Save the updated auth data
        self.update_auth_data(self.auth_data)
        
        return token

    def verify_token(self, username: str, token: str) -> bool:
        """
        Verify if a token is valid for a given user.
        
        Args:
            username (str): The username to check the token for
            token (str): The token to verify
            
        Returns:
            bool: True if the token is valid and not expired, False otherwise
        """
        if username not in self.auth_data["users"]:
            return False
            
        user_data = self.auth_data["users"][username]
        if "tokens" not in user_data or token not in user_data["tokens"]:
            return False
            
        token_data = user_data["tokens"][token]
        current_time = int(time.time())
        
        # Check if token has expired
        if current_time > token_data["expires_at"]:
            # Remove expired token
            del user_data["tokens"][token]
            self.update_auth_data(self.auth_data)
            return False
            
        return True

    def get_user_config(self, username: str, token: str) -> Dict[str, Any]:
        """
        Get the configuration for a user.
        
        Args:
            username (str): The username to get configuration for
        """
        if username not in self.auth_data["users"]:
            return None

        if token not in self.auth_data["users"][username]["tokens"]:
            return None

        return self.auth_data["users"][username]["config"]

    def update_auth_data(self, new_data: Dict[str, Any]) -> None:
        """
        Update the authentication data and save it to the file.
        
        Args:
            new_data (Dict[str, Any]): New authentication data to merge with existing data
        """
        self.auth_data.update(new_data)
        with open(self.config_path, 'w') as f:
            json.dump(self.auth_data, f, indent=4)
