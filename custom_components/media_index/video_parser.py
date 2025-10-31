"""Video metadata parser for MP4, MOV, and other video formats."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mutagen.mp4 import MP4
except ImportError:
    MP4 = None

_LOGGER = logging.getLogger(__name__)


class VideoMetadataParser:
    """Extract metadata from video files using mutagen."""

    @staticmethod
    def extract_metadata(file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata from a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dictionary containing extracted metadata, or None if extraction fails
        """
        if MP4 is None:
            _LOGGER.warning("mutagen not available, cannot extract video metadata")
            return None
            
        try:
            # Only process video files
            path = Path(file_path)
            if path.suffix.lower() not in {'.mp4', '.m4v', '.mov'}:
                return None
                
            video = MP4(file_path)
            if not video:
                return None
                
            result: Dict[str, Any] = {}
            
            # Extract creation date from MP4 atoms
            # MP4 files store creation dates in the movie/media/track header atoms
            # These are stored as seconds since midnight, January 1, 1904 UTC (MP4 epoch)
            creation_timestamp = None
            
            # Try to access raw MP4 atoms through mutagen's internal structure
            # The 'tags' attribute contains the moov.udta.meta atoms
            # We need to access moov.mvhd (Movie Header) for creation_time
            try:
                # Method 1: Try to access movie header creation time from file atoms
                # mutagen stores this in the MP4.info object
                if hasattr(video, 'info'):
                    # Check for various time fields that might be present
                    for time_attr in ['creation_time', 'modification_time']:
                        if hasattr(video.info, time_attr):
                            timestamp = getattr(video.info, time_attr)
                            if timestamp and timestamp > 0:
                                # MP4 timestamps are seconds since 1904-01-01 00:00:00 UTC
                                # Convert to Unix timestamp (seconds since 1970-01-01)
                                # Difference between 1904 and 1970 is 2,082,844,800 seconds
                                MP4_EPOCH_OFFSET = 2082844800
                                unix_timestamp = timestamp - MP4_EPOCH_OFFSET
                                
                                # Sanity check: timestamp should be reasonable (after 1990, before 2050)
                                if 631152000 < unix_timestamp < 2524608000:  # 1990-01-01 to 2050-01-01
                                    creation_timestamp = unix_timestamp
                                    _LOGGER.debug(f"Extracted {time_attr} from MP4: {unix_timestamp} ({datetime.fromtimestamp(unix_timestamp)})")
                                    break
            except Exception as e:
                _LOGGER.debug(f"Failed to extract creation time from MP4 atoms: {e}")
            
            # Method 2: Try QuickTime metadata tags (for files created by Apple devices)
            if not creation_timestamp and 'com.apple.quicktime.creationdate' in video:
                creation_date_str = video['com.apple.quicktime.creationdate'][0]
                parsed_date = VideoMetadataParser._parse_datetime(creation_date_str)
                if parsed_date:
                    try:
                        dt = datetime.strptime(parsed_date, '%Y-%m-%d %H:%M:%S')
                        creation_timestamp = int(dt.timestamp())
                    except ValueError:
                        pass
            
            # Method 3: Try copyright date (©day) as fallback
            if not creation_timestamp and '©day' in video and video['©day']:
                creation_date_str = video['©day'][0]
                parsed_date = VideoMetadataParser._parse_datetime(creation_date_str)
                if parsed_date:
                    try:
                        dt = datetime.strptime(parsed_date, '%Y-%m-%d %H:%M:%S')
                        creation_timestamp = int(dt.timestamp())
                    except ValueError:
                        pass
            
            if creation_timestamp:
                result['date_taken'] = creation_timestamp
            
            # Extract GPS coordinates from XMP if available
            # MP4 files can store GPS in com.apple.quicktime.location.ISO6709 or XMP
            if 'com.apple.quicktime.location.ISO6709' in video:
                iso6709 = video['com.apple.quicktime.location.ISO6709'][0]
                coords = VideoMetadataParser._parse_iso6709(iso6709)
                if coords:
                    result['latitude'] = coords[0]
                    result['longitude'] = coords[1]
                    result['has_coordinates'] = True
            
            # Extract rating
            # iTunes-style rating is stored in 'rate' or '----:com.apple.iTunes:rating'
            rating = None
            
            # Try iTunes rating first (0-5 stars * 20 = 0-100)
            if 'rate' in video:
                rate_value = video['rate'][0] if video['rate'] else None
                if rate_value:
                    # Convert 0-100 to 0-5 stars
                    rating = int(rate_value / 20)
            
            # Try custom iTunes rating tag
            if rating is None and '----:com.apple.iTunes:rating' in video:
                rating_bytes = video['----:com.apple.iTunes:rating'][0]
                try:
                    rating = int(rating_bytes.decode('utf-8'))
                except (ValueError, UnicodeDecodeError):
                    pass
            
            if rating is not None and 0 <= rating <= 5:
                result['rating'] = rating
            
            return result if result else None
            
        except Exception as e:
            _LOGGER.debug(f"Failed to extract video metadata from {file_path}: {e}")
            return None
    
    @staticmethod
    def _parse_datetime(date_str: str) -> Optional[str]:
        """Parse datetime from various video metadata formats.
        
        Args:
            date_str: Date string from video metadata
            
        Returns:
            ISO format datetime string, or None if parsing fails
        """
        if not date_str:
            return None
            
        # Try common video metadata date formats
        date_formats = [
            '%Y-%m-%dT%H:%M:%SZ',      # ISO 8601 with Z
            '%Y-%m-%dT%H:%M:%S',       # ISO 8601 without timezone
            '%Y-%m-%d %H:%M:%S',       # Standard datetime
            '%Y-%m-%d',                # Date only
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
                
        # If no format matches, return original string
        return date_str
    
    @staticmethod
    def _parse_iso6709(iso6709_str: str) -> Optional[tuple[float, float]]:
        """Parse ISO 6709 location string into latitude/longitude.
        
        ISO 6709 format: +40.7484-073.9857/ (latitude, longitude, optional altitude)
        
        Args:
            iso6709_str: ISO 6709 formatted location string
            
        Returns:
            Tuple of (latitude, longitude) or None if parsing fails
        """
        try:
            # Remove trailing slash if present
            iso6709_str = iso6709_str.rstrip('/')
            
            # Find the split between lat/lon (look for second +/-)
            # Format: +/-XX.XXXX+/-XXX.XXXX
            lat_end = 1  # Skip first sign
            while lat_end < len(iso6709_str) and iso6709_str[lat_end] not in ['+', '-']:
                lat_end += 1
            
            lat_str = iso6709_str[:lat_end]
            lon_str = iso6709_str[lat_end:].split('/')[0]  # Remove altitude if present
            
            latitude = float(lat_str)
            longitude = float(lon_str)
            
            return (latitude, longitude)
            
        except (ValueError, IndexError) as e:
            _LOGGER.debug(f"Failed to parse ISO 6709 location '{iso6709_str}': {e}")
            return None
    @staticmethod
    def write_rating(file_path: str, rating: int) -> bool:
        """Write rating to video file metadata.
        
        NOTE: Video rating writes are DISABLED due to technical limitations:
        - exiftool not accessible in Home Assistant executor thread context
        - mutagen can corrupt MP4 files when writing custom tags
        - exiftool requires re-encoding entire video for safe metadata writes
        
        Video ratings are persisted in the database only.
        Use the export/import backup services to preserve ratings across DB resets.
        
        Args:
            file_path: Path to the video file
            rating: Rating value (0-5 stars)
            
        Returns:
            False (video file writes disabled)
        """
        _LOGGER.debug(f"Video rating write skipped for {file_path} (database-only mode)")
        return False
