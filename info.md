# Media Index Integration

Indexes media files from local folders, extracts EXIF metadata, provides geocoding, and offers services for random media selection and file management.

## Key Features

- **Automatic media scanning** with real-time file monitoring
- **EXIF/metadata extraction** for images and videos
- **GPS coordinate geocoding** to location names
- **Smart random media selection** with exclusion tracking
- **Favorites and ratings** support (0-5 stars)
- **File management services** (delete, mark for editing)

## Installation

After installing via HACS:

1. Restart Home Assistant
2. Go to **Settings** → **Devices & Services**
3. Click **Add Integration**
4. Search for "Media Index" and follow the setup wizard

## Configuration

The integration will guide you through:

- Selecting media folders to scan
- Configuring file watcher settings
- Setting up geocoding preferences

## Services

The integration provides several services for use with automations and the Media Card:

- `media_index.get_random_media` - Get random media with filters
- `media_index.mark_favorite` - Toggle favorite status
- `media_index.delete_media` - Move files to _Junk folder
- `media_index.mark_for_edit` - Move files to _Edit folder

## Compatible Cards

Works perfectly with the **Home Assistant Media Card** for creating dynamic photo slideshows with metadata display.