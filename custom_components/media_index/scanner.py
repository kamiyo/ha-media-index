"""Media file scanner for Home Assistant."""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from homeassistant.core import HomeAssistant

from .cache_manager import CacheManager

_LOGGER = logging.getLogger(__name__)

# Media file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.heic'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.mpg', '.mpeg'}

class MediaScanner:
    """Scanner for media files."""
    
    def __init__(self, cache_manager: CacheManager, hass: HomeAssistant = None):
        """Initialize the scanner."""
        self.cache = cache_manager
        self.hass = hass
        self._is_scanning = False
        _LOGGER.info("MediaScanner initialized")
    
    @property
    def is_scanning(self) -> bool:
        """Return whether a scan is currently in progress."""
        return self._is_scanning
    
    def _is_media_file(self, file_path: str) -> bool:
        """Check if a file is a media file based on extension."""
        ext = Path(file_path).suffix.lower()
        return ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS
    
    def _get_file_type(self, file_path: str) -> Optional[str]:
        """Determine file type (image or video)."""
        ext = Path(file_path).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return "image"
        elif ext in VIDEO_EXTENSIONS:
            return "video"
        return None
    
    def _get_file_metadata(self, file_path: str) -> Optional[dict]:
        """Extract metadata from a media file."""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            path_obj = Path(file_path)
            
            return {
                "path": file_path,
                "filename": path_obj.name,
                "folder": str(path_obj.parent),
                "file_type": self._get_file_type(file_path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            }
        except Exception as err:
            _LOGGER.warning("Failed to get metadata for %s: %s", file_path, err)
            return None
    
    def _walk_directory(self, scan_path: str, max_depth: Optional[int] = None) -> list:
        """Walk directory tree and collect media files (blocking call for executor)."""
        media_files = []
        
        try:
            for root, _, files in os.walk(scan_path):
                # Check depth limit
                if max_depth is not None:
                    depth = root[len(scan_path):].count(os.sep)
                    if depth > max_depth:
                        continue
                
                # Process files in this directory
                for filename in files:
                    file_path = os.path.join(root, filename)
                    
                    # Skip non-media files
                    if not self._is_media_file(file_path):
                        continue
                    
                    # Get file metadata
                    metadata = self._get_file_metadata(file_path)
                    if metadata:
                        media_files.append(metadata)
        
        except Exception as err:
            _LOGGER.error("Error walking directory %s: %s", scan_path, err)
        
        return media_files
    
    async def scan_folder(
        self,
        base_folder: str,
        watched_folders: Optional[list] = None,
        max_depth: Optional[int] = None,
    ) -> int:
        """Scan a folder for media files and update cache.
        
        Args:
            base_folder: Base media folder path
            watched_folders: Optional list of subfolders to watch (empty = watch all)
            max_depth: Maximum depth to scan (None = unlimited)
        
        Returns:
            Number of files added to cache
        """
        if self._is_scanning:
            _LOGGER.warning("Scan already in progress")
            return 0
        
        self._is_scanning = True
        files_added = 0
        
        try:
            _LOGGER.info("Starting full scan of %s", base_folder)
            
            # Record scan start
            scan_id = await self.cache.record_scan(base_folder, watched_folders or [])
            
            # Determine paths to scan
            scan_paths = []
            if watched_folders:
                for folder in watched_folders:
                    folder_path = os.path.join(base_folder, folder)
                    if os.path.exists(folder_path):
                        scan_paths.append(folder_path)
                    else:
                        _LOGGER.warning("Watched folder not found: %s", folder_path)
            else:
                # Scan entire base folder
                scan_paths = [base_folder]
            
            # Scan each path (run blocking I/O in executor)
            for scan_path in scan_paths:
                if not os.path.exists(scan_path):
                    _LOGGER.warning("Path does not exist: %s", scan_path)
                    continue
                
                _LOGGER.info("Scanning: %s", scan_path)
                
                # Run blocking directory walk in executor
                if self.hass:
                    media_files = await self.hass.async_add_executor_job(
                        self._walk_directory, scan_path, max_depth
                    )
                else:
                    # Fallback for testing without hass
                    media_files = self._walk_directory(scan_path, max_depth)
                
                # Add files to cache
                for metadata in media_files:
                    try:
                        await self.cache.add_file(metadata)
                        files_added += 1
                        
                        if files_added % 100 == 0:
                            _LOGGER.debug("Indexed %d files so far...", files_added)
                    
                    except Exception as err:
                        _LOGGER.error("Failed to add file to cache: %s - %s", metadata.get("path"), err)
            
            # Update scan record
            await self.cache.update_scan(scan_id, files_added, "completed")
            
            _LOGGER.info("Scan complete. Added %d files to cache", files_added)
            return files_added
        
        except Exception as err:
            _LOGGER.error("Scan failed: %s", err)
            if scan_id:
                await self.cache.update_scan(scan_id, files_added, "failed")
            return files_added
        
        finally:
            self._is_scanning = False
