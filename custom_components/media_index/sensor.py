"""Sensor platform for Media Index integration."""
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_SCAN_STATUS,
    ATTR_LAST_SCAN_TIME,
    ATTR_TOTAL_FOLDERS,
    ATTR_TOTAL_IMAGES,
    ATTR_TOTAL_VIDEOS,
    ATTR_WATCHED_FOLDERS,
    ATTR_CACHE_SIZE_MB,
    ATTR_GEOCODE_CACHE_ENTRIES,
    ATTR_GEOCODE_HIT_RATE,
    ATTR_FILES_WITH_LOCATION,
    SCAN_STATUS_IDLE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Media Index sensors from a config entry."""
    _LOGGER.info("Setting up Media Index sensor")
    
    # Create sensors
    async_add_entities(
        [
            MediaIndexTotalFilesSensor(hass, entry),
        ],
        True,
    )


class MediaIndexTotalFilesSensor(SensorEntity):
    """Sensor showing total indexed files."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attr_name = "Media Index Total Files"
        self._attr_unique_id = f"{entry.entry_id}_total_files"
        self._attr_icon = "mdi:folder-multiple-image"
        self._attr_native_value = 0
        
        # Attributes
        self._attr_extra_state_attributes = {
            ATTR_SCAN_STATUS: SCAN_STATUS_IDLE,
            ATTR_LAST_SCAN_TIME: None,
            ATTR_TOTAL_FOLDERS: 0,
            ATTR_TOTAL_IMAGES: 0,
            ATTR_TOTAL_VIDEOS: 0,
            ATTR_WATCHED_FOLDERS: [],
            ATTR_CACHE_SIZE_MB: 0.0,
            ATTR_GEOCODE_CACHE_ENTRIES: 0,
            ATTR_GEOCODE_HIT_RATE: 0.0,
            ATTR_FILES_WITH_LOCATION: 0,
        }
    
    @property
    def device_info(self):
        """Return device information about this sensor."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Media Index",
            "manufacturer": "Media Index Integration",
            "model": "Media Index",
            "sw_version": "1.0.0",
        }
    
    async def async_update(self) -> None:
        """Update the sensor."""
        _LOGGER.debug("Updating Media Index sensor")
        
        # Get cache manager from hass data
        cache_manager = self.hass.data[DOMAIN][self._entry.entry_id].get("cache_manager")
        scanner = self.hass.data[DOMAIN][self._entry.entry_id].get("scanner")
        
        if not cache_manager:
            _LOGGER.warning("Cache manager not initialized")
            return
        
        # Get cache statistics
        stats = await cache_manager.get_cache_stats()
        
        # Update sensor state (total files)
        self._attr_native_value = stats.get("total_files", 0)
        
        # Update attributes
        scan_status = SCAN_STATUS_IDLE
        if scanner and scanner.is_scanning:
            scan_status = "scanning"
        
        self._attr_extra_state_attributes = {
            ATTR_SCAN_STATUS: scan_status,
            ATTR_LAST_SCAN_TIME: stats.get("last_scan_time"),
            ATTR_TOTAL_FOLDERS: stats.get("total_folders", 0),
            ATTR_TOTAL_IMAGES: stats.get("total_images", 0),
            ATTR_TOTAL_VIDEOS: stats.get("total_videos", 0),
            ATTR_WATCHED_FOLDERS: [],  # TODO: Get from config
            ATTR_CACHE_SIZE_MB: stats.get("cache_size_mb", 0.0),
            ATTR_GEOCODE_CACHE_ENTRIES: stats.get("geocode_cache_entries", 0),
            ATTR_GEOCODE_HIT_RATE: 0.0,  # TODO: Calculate
            ATTR_FILES_WITH_LOCATION: stats.get("files_with_location", 0),
        }
