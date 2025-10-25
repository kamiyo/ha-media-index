# Media Index - Home Assistant Integration

Efficiently scan, index, and serve media metadata for Home Assistant. Designed for large collections (25,000+ files) with intelligent caching and incremental updates.

## Features

- ✅ **Smart Caching** - SQLite-based caching system prevents full scans on every restart
- ✅ **Incremental Scanning** - Only scans new/modified files
- ✅ **File System Monitoring** - Real-time updates with watchdog integration
- ✅ **EXIF Metadata** - Extracts camera, date, and GPS information
- ✅ **Geocoding** - Converts GPS coordinates to location names (cached)
- ✅ **UI Configuration** - Full reconfiguration via Home Assistant UI
- ✅ **Performance Optimized** - Concurrent scanning, batching, and background processing

## Installation

### HACS (Recommended)
1. Open HACS in Home Assistant
2. Click "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add `https://github.com/markaggar/ha-media-index` as an Integration
5. Click "Install"
6. Restart Home Assistant

### Manual
1. Copy the `custom_components/media_index` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Media Index"
4. Enter your base media folder path (e.g., `/media/Photos`)
5. Configure optional settings (watched folders, EXIF extraction, geocoding)

### Reconfiguration

Click **Configure** on the Media Index integration to change:
- Watched folders (real-time monitoring)
- Scan schedule (startup_only, hourly, daily, weekly)
- EXIF extraction (on/off)
- Geocoding (on/off and precision)
- Performance settings (concurrent scans, batch size, cache age)

No restart required for configuration changes!

## Sensor

The integration creates a `sensor.media_index_total_files` entity with the following attributes:

- `scan_status`: Current scan state (`idle`, `scanning`, `watching`)
- `last_scan_time`: ISO timestamp of last scan completion
- `total_folders`: Number of folders indexed
- `total_images`: Count of image files
- `total_videos`: Count of video files
- `watched_folders`: List of folders with active file system watchers
- `cache_size_mb`: Size of SQLite cache database
- `geocode_cache_entries`: Number of cached location lookups
- `geocode_cache_hit_rate`: Percentage of GPS lookups served from cache
- `files_with_location`: Count of files with GPS coordinates

## Development

### Setup

```powershell
# Clone the repository
git clone https://github.com/markaggar/ha-media-index
cd ha-media-index

# Set environment variables
$env:HA_BASE_URL = "http://10.0.0.62:8123"
$env:HA_TOKEN = "your-long-lived-access-token"
$env:HA_VERIFY_ENTITY = "sensor.media_index_total_files"
```

### Automated Deployment

```powershell
# Deploy and verify
.\scripts\deploy-media-index.ps1 `
    -DestPath "\\10.0.0.62\config\custom_components\media_index" `
    -VerifyEntity "sensor.media_index_total_files" `
    -DumpErrorLogOnFail
```

The deployment script will:
1. Copy changed files to HA server
2. Validate HA configuration
3. Restart Home Assistant
4. Wait for HA to come back online
5. Verify integration loaded successfully
6. Check sensor attributes are populated

### Testing

```powershell
# Run unit tests
pytest tests/ -v --cov=custom_components/media_index

# Integration test (deploy + verify)
.\scripts\deploy-media-index.ps1 -VerifyEntity "sensor.media_index_total_files" -DumpErrorLogOnFail
if ($LASTEXITCODE -eq 0) { 
    Write-Host "✅ Integration deployed successfully" -ForegroundColor Green 
}
```

## Services

(Coming in v1.1)

- `media_index.scan_folder` - Trigger manual scan
- `media_index.get_random_items` - Get random media items (for slideshows)
- `media_index.favorite_file` - Mark file as favorite
- `media_index.rate_file` - Rate file (1-5 stars)
- `media_index.delete_file` - Delete file
- `media_index.move_file` - Move file to different folder

## Performance

- **Initial scan:** 25,000 files in ~2 minutes
- **Incremental scan:** <10 seconds
- **Real-time updates:** File changes detected within 5 seconds
- **Service queries:** <100ms response time
- **Integration load time:** <5 seconds on HA restart

## Geocoding

Uses Nominatim (OpenStreetMap) for free reverse geocoding:
- No API key required
- 1 request/second rate limit (automatically enforced)
- Coordinates rounded to 4 decimal places (~11m precision) for cache grouping
- Expected cache hit rate: 60-80% for typical photo collections

## Version History

### v1.0.0 (Current)
- Initial release
- Smart caching system
- Incremental scanning
- Basic sensor with attributes
- UI configuration and reconfiguration
- Automated deployment script

## License

MIT License - see LICENSE file for details

## Credits

Created by Mark Aggarwal for the Home Assistant community.
