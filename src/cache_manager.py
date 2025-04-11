import os
import json
import pickle
from typing import Any, Optional, Union, Dict
import hashlib
import time

class CacheManager:
    """
    A class to manage a cache directory with get and set methods.
    """
    
    def __init__(self, cache_dir: str = "src/web/cache", default_expiration: int = 600):
        """
        Initialize the cache manager with the specified cache directory.
        
        Args:
            cache_dir: The directory where cache files will be stored.
            default_expiration: Default expiration time in seconds (default: 600 seconds / 10 minutes)
        """
        self.cache_dir = cache_dir
        self.default_expiration = default_expiration
        self.manifest_path = os.path.join(cache_dir, "manifest.json")
        self._ensure_cache_dir_exists()
        self._load_manifest()
    
    def _ensure_cache_dir_exists(self) -> None:
        """Ensure the cache directory exists, creating it if necessary."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def _load_manifest(self) -> None:
        """Load the cache manifest from disk or create a new one if it doesn't exist."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    self.manifest = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.manifest = {}
        else:
            self.manifest = {}
    
    def _save_manifest(self) -> None:
        """Save the cache manifest to disk."""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f)
        except IOError as e:
            print(f"Error saving manifest: {e}")
    
    def _get_cache_path(self, key: str) -> str:
        """
        Get the path to the cache file for the given key.
        
        Args:
            key: The cache key.
            
        Returns:
            The path to the cache file.
        """
        # Hash the key to create a safe filename
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get data from the cache.
        
        Args:
            key: The cache key.
            default: The default value to return if the key is not found.
            
        Returns:
            The cached data or the default value if not found.
        """
        cache_path = self._get_cache_path(key)
        
        # Check if the key exists in the manifest and is not expired
        if key in self.manifest:
            expiration_time = self.manifest[key].get('expiration_time', 0)
            if time.time() > expiration_time:
                # Cache item has expired, delete it
                self.delete(key)
                return default
        
        if not os.path.exists(cache_path):
            return default
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, EOFError, FileNotFoundError):
            # If there's an error reading the cache, return the default
            return default
    
    def set(self, key: str, data: Any, expiration: Optional[int] = None) -> None:
        """
        Store data in the cache.
        
        Args:
            key: The cache key.
            data: The data to store.
            expiration: Optional expiration time in seconds. If None, uses default_expiration.
        """
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            # Update manifest with expiration time
            expiration_time = time.time() + (expiration if expiration is not None else self.default_expiration)
            self.manifest[key] = {
                'expiration_time': expiration_time,
                'cache_path': cache_path
            }
            self._save_manifest()
        except (pickle.PickleError, IOError) as e:
            print(f"Error writing to cache: {e}")
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.
        
        Args:
            key: The cache key.
            
        Returns:
            True if the key was deleted, False otherwise.
        """
        cache_path = self._get_cache_path(key)
        
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                if key in self.manifest:
                    del self.manifest[key]
                    self._save_manifest()
                return True
            except OSError:
                return False
        
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.cache'):
                try:
                    os.remove(os.path.join(self.cache_dir, filename))
                except OSError:
                    pass
        
        # Clear the manifest
        self.manifest = {}
        self._save_manifest()
    
    def delete_expired(self) -> None:
        """Delete all expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, info in self.manifest.items()
            if current_time > info.get('expiration_time', 0)
        ]
        
        for key in expired_keys:
            self.delete(key) 