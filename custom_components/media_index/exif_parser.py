"""EXIF data extraction for media files."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import piexif

_LOGGER = logging.getLogger(__name__)


class ExifParser:
    """Extract EXIF metadata from image files."""

    @staticmethod
    def _convert_to_degrees(value) -> Optional[float]:
        """Convert GPS coordinates from DMS (degrees, minutes, seconds) to decimal degrees.
        
        Args:
            value: Tuple of (degrees, minutes, seconds) as Rational numbers
            
        Returns:
            Decimal degrees as float, or None if conversion fails
        """
        try:
            d, m, s = value
            # Convert Rational to float
            degrees = float(d)
            minutes = float(m) / 60.0
            seconds = float(s) / 3600.0
            return degrees + minutes + seconds
        except (TypeError, ValueError, ZeroDivisionError) as err:
            _LOGGER.debug("Failed to convert GPS coordinates: %s", err)
            return None

    @staticmethod
    def _get_gps_coordinates(gps_info: dict) -> tuple[Optional[float], Optional[float]]:
        """Extract latitude and longitude from GPS info.
        
        Args:
            gps_info: Dictionary of GPS EXIF tags
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if not available
        """
        try:
            # Get GPS latitude
            lat = gps_info.get('GPSLatitude')
            lat_ref = gps_info.get('GPSLatitudeRef')
            
            # Get GPS longitude
            lon = gps_info.get('GPSLongitude')
            lon_ref = gps_info.get('GPSLongitudeRef')
            
            if lat and lon and lat_ref and lon_ref:
                # Convert to decimal degrees
                latitude = ExifParser._convert_to_degrees(lat)
                longitude = ExifParser._convert_to_degrees(lon)
                
                if latitude is None or longitude is None:
                    return None, None
                
                # Apply hemisphere reference (N/S for latitude, E/W for longitude)
                if lat_ref == 'S':
                    latitude = -latitude
                if lon_ref == 'W':
                    longitude = -longitude
                
                return latitude, longitude
            
            return None, None
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.debug("Failed to extract GPS coordinates: %s", err)
            return None, None

    @staticmethod
    def _parse_datetime(exif_datetime: str) -> Optional[int]:
        """Parse EXIF datetime string to Unix timestamp.
        
        Args:
            exif_datetime: EXIF datetime string (format: "YYYY:MM:DD HH:MM:SS")
            
        Returns:
            Unix timestamp (seconds since epoch), or None if parsing fails
        """
        try:
            # EXIF datetime format: "2023:10:26 14:30:45"
            dt = datetime.strptime(exif_datetime, "%Y:%m:%d %H:%M:%S")
            return int(dt.timestamp())
        except (ValueError, TypeError) as err:
            _LOGGER.debug("Failed to parse EXIF datetime '%s': %s", exif_datetime, err)
            return None

    @staticmethod
    def _convert_to_float(value) -> Optional[float]:
        """Convert EXIF Rational or int to float.
        
        Args:
            value: EXIF value (can be Rational, int, or tuple)
            
        Returns:
            Float value, or None if conversion fails
        """
        try:
            if isinstance(value, tuple):
                # Handle rational numbers (numerator, denominator)
                if len(value) == 2 and value[1] != 0:
                    return float(value[0]) / float(value[1])
                return None
            return float(value)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def extract_exif(file_path: str) -> Optional[Dict[str, Any]]:
        """Extract EXIF metadata from an image file.
        
        Args:
            file_path: Full path to the image file
            
        Returns:
            Dictionary with EXIF data, or None if extraction fails
        """
        try:
            # Only process image files
            path = Path(file_path)
            if path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic'}:
                return None
            
            # Open image and get EXIF data
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                
                if not exif_data:
                    _LOGGER.debug("No EXIF data found in: %s", file_path)
                    return None
                
                # Parse EXIF tags
                exif = {}
                gps_info = {}
                
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    
                    # Extract GPS info separately
                    if tag_name == 'GPSInfo':
                        for gps_tag_id, gps_value in value.items():
                            gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_info[gps_tag_name] = gps_value
                    else:
                        exif[tag_name] = value
                
                # Build result dictionary
                result = {
                    'camera_make': exif.get('Make'),
                    'camera_model': exif.get('Model'),
                    'date_taken': None,
                    'latitude': None,
                    'longitude': None,
                    'iso': None,
                    'aperture': None,
                    'shutter_speed': None,
                    'focal_length': None,
                    'flash': None,
                    'rating': None,
                }
                
                # Parse date taken
                datetime_original = exif.get('DateTimeOriginal') or exif.get('DateTime')
                if datetime_original:
                    result['date_taken'] = ExifParser._parse_datetime(datetime_original)
                
                # Parse GPS coordinates
                if gps_info:
                    lat, lon = ExifParser._get_gps_coordinates(gps_info)
                    result['latitude'] = lat
                    result['longitude'] = lon
                
                # Parse camera settings
                if 'ISOSpeedRatings' in exif:
                    result['iso'] = int(exif['ISOSpeedRatings'])
                
                if 'FNumber' in exif:
                    f_number = ExifParser._convert_to_float(exif['FNumber'])
                    if f_number:
                        result['aperture'] = f_number
                
                if 'ExposureTime' in exif:
                    exposure = ExifParser._convert_to_float(exif['ExposureTime'])
                    if exposure:
                        # Format as fraction (e.g., "1/250")
                        if exposure < 1:
                            result['shutter_speed'] = f"1/{int(1/exposure)}"
                        else:
                            result['shutter_speed'] = f"{exposure:.1f}s"
                
                if 'FocalLength' in exif:
                    focal = ExifParser._convert_to_float(exif['FocalLength'])
                    if focal:
                        result['focal_length'] = focal
                
                if 'Flash' in exif:
                    flash_value = exif['Flash']
                    # Flash value is a bitmask; bit 0 indicates if flash fired
                    result['flash'] = 'Yes' if (flash_value & 1) else 'No'
                
                # Parse XMP:Rating (stored in EXIF Rating tag or XMP metadata)
                # Check standard Rating tag first (tag 0x4746)
                if 'Rating' in exif:
                    rating = exif['Rating']
                    if isinstance(rating, int) and 0 <= rating <= 5:
                        result['rating'] = rating
                
                _LOGGER.debug("Extracted EXIF from %s: date_taken=%s, GPS=(%s, %s)", 
                            path.name, result['date_taken'], result['latitude'], result['longitude'])
                
                return result
                
        except Exception as err:
            _LOGGER.warning("Failed to extract EXIF from %s: %s", file_path, err)
            return None

    @staticmethod
    def write_rating(file_path: str, rating: int) -> bool:
        """Write XMP:Rating metadata to an image file.
        
        Args:
            file_path: Full path to the image file
            rating: Rating value (0-5, where 0 means no rating/unfavorited)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Only process JPEG files (piexif supports JPEG only)
            path = Path(file_path)
            if path.suffix.lower() not in {'.jpg', '.jpeg'}:
                _LOGGER.debug("Skipping rating write for non-JPEG file: %s", file_path)
                return False
            
            # Validate rating value
            if not isinstance(rating, int) or rating < 0 or rating > 5:
                _LOGGER.warning("Invalid rating value %s, must be 0-5", rating)
                return False
            
            # Load existing EXIF data
            try:
                exif_dict = piexif.load(file_path)
            except Exception:
                # If no EXIF exists, create a new structure
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
            
            # Set Rating tag (0x4746 in IFD0)
            # Rating value: 0-5 where 0=no rating, 5=5 stars
            exif_dict["0th"][piexif.ImageIFD.Rating] = rating
            
            # Convert to bytes and write back to file
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, file_path)
            
            _LOGGER.debug("Wrote rating %d to %s", rating, path.name)
            return True
            
        except Exception as err:
            _LOGGER.warning("Failed to write rating to %s: %s", file_path, err)
            return False
