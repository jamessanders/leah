import os
import json
import pickle
from typing import Any, Optional, Union
import hashlib

class CacheManager:
    """
    A class to manage a cache directory with get and set methods.
    """
    
    def __init__(self, cache_dir: str = "src/web/cache"):
        """
        Initialize the cache manager with the specified cache directory.
        
        Args:
            cache_dir: The directory where cache files will be stored.
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir_exists()
    
    def _ensure_cache_dir_exists(self) -> None:
        """Ensure the cache directory exists, creating it if necessary."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
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
        
        if not os.path.exists(cache_path):
            return default
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, EOFError, FileNotFoundError):
            # If there's an error reading the cache, return the default
            return default
    
    def set(self, key: str, data: Any) -> None:
        """
        Store data in the cache.
        
        Args:
            key: The cache key.
            data: The data to store.
        """
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
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