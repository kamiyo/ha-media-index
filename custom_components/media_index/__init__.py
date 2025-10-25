"""Media Index integration for Home Assistant."""
import logging
import os
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_BASE_FOLDER,
    CONF_WATCHED_FOLDERS,
    CONF_SCAN_ON_STARTUP,
)
from .cache_manager import CacheManager
from .scanner import MediaScanner

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Media Index integration from YAML (not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Media Index from a config entry."""
    _LOGGER.info("Setting up Media Index integration")

    # Create integration data storage
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    # Initialize cache manager
    cache_db_path = os.path.join(hass.config.path(".storage"), "media_index.db")
    cache_manager = CacheManager(cache_db_path)
    
    if not await cache_manager.async_setup():
        _LOGGER.error("Failed to initialize cache manager")
        return False
    
    _LOGGER.info("Cache manager initialized successfully")
    
    # Initialize scanner
    scanner = MediaScanner(cache_manager, hass)
    
    # Store instances
    hass.data[DOMAIN][entry.entry_id]["cache_manager"] = cache_manager
    hass.data[DOMAIN][entry.entry_id]["scanner"] = scanner
    hass.data[DOMAIN][entry.entry_id]["config"] = {**entry.data, **entry.options}
    
    # Set up platforms BEFORE starting scan so sensor exists
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Trigger initial scan if configured
    config = {**entry.data, **entry.options}
    if config.get(CONF_SCAN_ON_STARTUP, True):
        base_folder = config.get(CONF_BASE_FOLDER, "/media")
        watched_folders = config.get(CONF_WATCHED_FOLDERS, [])
        
        _LOGGER.info("Starting initial scan of %s (watched: %s)", base_folder, watched_folders)
        
        # Start scan as background task
        hass.async_create_task(
            scanner.scan_folder(base_folder, watched_folders)
        )

    # Register update listener for config changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("Media Index integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Media Index integration")
    
    # Close cache manager
    cache_manager = hass.data[DOMAIN][entry.entry_id].get("cache_manager")
    if cache_manager:
        await cache_manager.close()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    _LOGGER.info("Reloading Media Index integration due to config change")
    await hass.config_entries.async_reload(entry.entry_id)

