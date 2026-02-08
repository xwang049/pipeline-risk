"""Utility functions for the pipeline"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class CacheManager:
    """Simple file-based cache for API responses"""
    
    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600
    
    def _get_cache_key(self, prefix: str, data: Any) -> str:
        """Generate cache key from prefix and data"""
        cache_input = f"{prefix}:{json.dumps(data, sort_keys=True, default=str)}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get(self, prefix: str, data: Any) -> Optional[Any]:
        """
        Get cached data if it exists and is not expired
        
        Args:
            prefix: Cache key prefix
            data: Input data used to generate cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        cache_key = self._get_cache_key(prefix, data)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        # Check if cache is expired
        cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if (datetime.now() - cache_time).total_seconds() > self.ttl_seconds:
            logger.debug(f"Cache expired for {cache_key}")
            cache_file.unlink(missing_ok=True)
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data
        except Exception as e:
            logger.warning(f"Error reading cache file {cache_file}: {e}")
            cache_file.unlink(missing_ok=True)
            return None
    
    def set(self, prefix: str, data: Any, result: Any) -> None:
        """
        Store data in cache
        
        Args:
            prefix: Cache key prefix
            data: Input data used to generate cache key
            result: Result to cache
        """
        cache_key = self._get_cache_key(prefix, data)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cached data for {cache_key}")
        except Exception as e:
            logger.error(f"Error writing cache file {cache_file}: {e}")


# Global cache instance
cache_manager = CacheManager()