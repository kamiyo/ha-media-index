"""SQLite cache manager for media file indexing."""
import aiosqlite
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List, Any

_LOGGER = logging.getLogger(__name__)

class CacheManager:
    """Manage SQLite cache for media files."""
    
    def __init__(self, db_path: str):
        """Initialize cache manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        _LOGGER.info("CacheManager initialized with database: %s", db_path)
    
    async def async_setup(self) -> bool:
        """Set up database connection and schema.
        
        Returns:
            True if setup successful
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
            
            # Create schema
            await self._create_schema()
            
            _LOGGER.info("Cache database initialized successfully")
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to initialize cache database: %s", e)
            return False
    
    async def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                folder TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                modified_time INTEGER NOT NULL,
                created_time INTEGER,
                duration REAL,
                width INTEGER,
                height INTEGER,
                orientation TEXT,
                last_scanned INTEGER NOT NULL,
                is_favorited INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 0,
                rated_at INTEGER
            )
        """)
        
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_folder ON media_files(folder)
        """)
        
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_modified ON media_files(modified_time)
        """)
        
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON media_files(file_type)
        """)
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS exif_data (
                file_id INTEGER PRIMARY KEY,
                camera_make TEXT,
                camera_model TEXT,
                date_taken INTEGER,
                latitude REAL,
                longitude REAL,
                location_name TEXT,
                location_city TEXT,
                location_country TEXT,
                iso INTEGER,
                aperture REAL,
                shutter_speed TEXT,
                focal_length REAL,
                flash TEXT,
                FOREIGN KEY (file_id) REFERENCES media_files(id) ON DELETE CASCADE
            )
        """)
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS geocode_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                precision_level INTEGER NOT NULL,
                location_name TEXT,
                city TEXT,
                country TEXT,
                cached_at INTEGER NOT NULL,
                UNIQUE(latitude, longitude, precision_level)
            )
        """)
        
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_geocode_coords 
            ON geocode_cache(latitude, longitude, precision_level)
        """)
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT NOT NULL,
                scan_type TEXT NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER,
                files_added INTEGER DEFAULT 0,
                files_updated INTEGER DEFAULT 0,
                files_removed INTEGER DEFAULT 0,
                status TEXT
            )
        """)
        
        await self._db.commit()
        _LOGGER.debug("Database schema created/verified")
    
    async def get_total_files(self) -> int:
        """Get total number of indexed files.
        
        Returns:
            Total file count
        """
        async with self._db.execute("SELECT COUNT(*) FROM media_files") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def get_total_by_type(self, file_type: str) -> int:
        """Get total files of specific type.
        
        Args:
            file_type: File type (image, video)
            
        Returns:
            Count of files
        """
        async with self._db.execute(
            "SELECT COUNT(*) FROM media_files WHERE file_type = ?",
            (file_type,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def get_total_folders(self) -> int:
        """Get number of unique folders.
        
        Returns:
            Folder count
        """
        async with self._db.execute(
            "SELECT COUNT(DISTINCT folder) FROM media_files"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_files = await self.get_total_files()
        total_images = await self.get_total_by_type('image')
        total_videos = await self.get_total_by_type('video')
        total_folders = await self.get_total_folders()
        
        # Get database file size
        cache_size_mb = 0.0
        if os.path.exists(self.db_path):
            cache_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        
        # Get files with location data
        async with self._db.execute(
            "SELECT COUNT(*) FROM exif_data WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        ) as cursor:
            row = await cursor.fetchone()
            files_with_location = row[0] if row else 0
        
        # Get geocode cache stats
        async with self._db.execute("SELECT COUNT(*) FROM geocode_cache") as cursor:
            row = await cursor.fetchone()
            geocode_cache_entries = row[0] if row else 0
        
        # Get last scan time
        last_scan_time = None
        async with self._db.execute(
            "SELECT MAX(end_time) FROM scan_history WHERE status = 'completed'"
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                last_scan_time = datetime.fromtimestamp(row[0]).isoformat()
        
        return {
            "total_files": total_files,
            "total_images": total_images,
            "total_videos": total_videos,
            "total_folders": total_folders,
            "cache_size_mb": round(cache_size_mb, 2),
            "files_with_location": files_with_location,
            "geocode_cache_entries": geocode_cache_entries,
            "last_scan_time": last_scan_time,
        }
    
    async def add_file(self, file_data: Dict[str, Any]) -> int:
        """Add file to cache.
        
        Args:
            file_data: File metadata dictionary
            
        Returns:
            File ID
        """
        await self._db.execute("""
            INSERT OR REPLACE INTO media_files 
            (path, filename, folder, file_type, file_size, modified_time, 
             created_time, last_scanned, orientation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_data['path'],
            file_data['filename'],
            file_data['folder'],
            file_data['file_type'],
            file_data.get('file_size'),
            file_data['modified_time'],
            file_data.get('created_time'),
            int(datetime.now().timestamp()),
            file_data.get('orientation'),
        ))
        
        await self._db.commit()
        
        # Get the file ID
        async with self._db.execute(
            "SELECT id FROM media_files WHERE path = ?",
            (file_data['path'],)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def record_scan(self, folder_path: str, scan_type: str) -> int:
        """Record start of scan.
        
        Args:
            folder_path: Path being scanned
            scan_type: Type of scan (full, incremental)
            
        Returns:
            Scan history ID
        """
        await self._db.execute("""
            INSERT INTO scan_history 
            (folder_path, scan_type, start_time, status)
            VALUES (?, ?, ?, 'running')
        """, (folder_path, scan_type, int(datetime.now().timestamp())))
        
        await self._db.commit()
        
        async with self._db.execute(
            "SELECT last_insert_rowid()"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def update_scan(self, scan_id: int, files_added: int = 0, 
                         files_updated: int = 0, status: str = 'completed') -> None:
        """Update scan record.
        
        Args:
            scan_id: Scan history ID
            files_added: Number of files added
            files_updated: Number of files updated
            status: Final status
        """
        await self._db.execute("""
            UPDATE scan_history 
            SET end_time = ?, files_added = ?, files_updated = ?, status = ?
            WHERE id = ?
        """, (
            int(datetime.now().timestamp()),
            files_added,
            files_updated,
            status,
            scan_id
        ))
        
        await self._db.commit()
    
    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            _LOGGER.info("Cache database connection closed")
