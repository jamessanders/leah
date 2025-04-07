#!/usr/bin/env python3

"""
Config - A module for managing configuration settings for the Leah script.
"""

import os
import json
from typing import Dict, Any
from copy import deepcopy


class Config:
    """Configuration management class for the Leah script."""
    
    def __init__(self):
        """Initialize the configuration by loading from config.json."""
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json and merge with .hey.config.json if it exists."""
        # Load the main config file
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Check for user config in home directory
        home_dir = os.path.expanduser("~")
        user_config_path = os.path.join(home_dir, '.hey.config.json')
        
        if os.path.exists(user_config_path):
            print("User config found")
            try:
                with open(user_config_path, 'r') as f:
                    user_config = json.load(f)
                
                # Merge user config with main config
                config = self._merge_configs(config, user_config)
            except Exception as e:
                print(e)
        
        return config
    
    def _merge_configs(self, main_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with main config, with user config taking precedence."""
        # Create a deep copy of the main config to avoid modifying it
        merged_config = deepcopy(main_config)
        
        # Merge top-level keys
        for key, value in user_config.items():
            if key not in merged_config:
                merged_config[key] = value
            elif isinstance(value, dict) and isinstance(merged_config[key], dict):
                # Recursively merge dictionaries
                merged_config[key] = self._merge_configs(merged_config[key], value)
            else:
                # User config takes precedence
                merged_config[key] = value
        
        return merged_config
    
    def _get_persona_config(self, persona='default') -> Dict[str, Any]:
        """Get the configuration for a persona, merging with default if needed."""
        if persona == 'default':
            return self.config['personas']['default']
        
        # Start with a deep copy of the default persona
        persona_config = deepcopy(self.config['personas']['default'])
        
        # Merge in the selected persona's settings
        if persona in self.config['personas']:
            for key, value in self.config['personas'][persona].items():
                persona_config[key] = value
        
        return persona_config
    
    def get_system_content(self, persona='default') -> str:
        """Get the system content based on the specified persona."""
        persona_config = self._get_persona_config(persona)
        return f"{persona_config['description']}\n" + "\n".join(f"- {trait}" for trait in persona_config['traits'])
    
    def get_model(self, persona='default') -> str:
        """Get the model for the specified persona."""
        return self._get_persona_config(persona)['model']
    
    def get_temperature(self, persona='default') -> float:
        """Get the temperature setting for the specified persona."""
        return self._get_persona_config(persona)['temperature']
    
    def get_prompt_script(self, persona='default') -> str:
        """Get the prompt script for the specified persona."""
        print(self._get_persona_config(persona))
        return self._get_persona_config(persona)['prompt_script']  
    
    def get_voice(self, persona='default') -> str:
        """Get the voice for the specified persona."""
        return self._get_persona_config(persona)['voice']
    
    def get_ollama_url(self) -> str:
        """Get the LMStudio API URL from config."""
        return self.config['url']
    
    def get_headers(self) -> Dict[str, str]:
        """Get the headers from config."""
        return self.config['headers']
    
    def get_persona_choices(self) -> list:
        """Get the list of available personas."""
        return list(self.config['personas'].keys()) 