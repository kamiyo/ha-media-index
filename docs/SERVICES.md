# Media Index Services

This document describes all available services provided by the Media Index integration.

## Multi-Instance Support

All services support multiple integration instances using Home Assistant's target selector:

```yaml
service: media_index.restore_edited_files
target:
  entity_id: sensor.media_index_photos_total_files
```

**Target Options:**
- `entity_id: sensor.media_index_photos_total_files` - Target specific instance
- Omit target - Operates on all configured instances

## User Services

### `media_index.restore_edited_files`

**Most Important for End Users** - Move files from `_Edit` folder back to their original locations.

**Parameters:** None (restores all files in `_Edit` folders)

**How it works:**
- Tracks original file paths when moving to `_Edit`
- Stores move history in database
- Service reads history and restores files to original locations
- Updates database to reflect new locations

**Use cases:**
- Complete editing workflow after making corrections
- Bulk restore after batch editing in external applications
- Undo accidental moves to `_Edit` folder

**Example:**
```yaml
service: media_index.restore_edited_files
```

**Recommendation:** Run this service periodically (weekly/monthly) as part of your media management workflow.

## Media Query Services

### `media_index.get_random_items`

Get random media files from the index (used by Media Card).

**Parameters:**
- `count` (optional, default: 10): Number of items to return
- `folder` (optional): Filter by specific folder
- `file_type` (optional): Filter by `image` or `video`
- `date_from` (optional): ISO date string (YYYY-MM-DD)
- `date_to` (optional): ISO date string (YYYY-MM-DD)
- `favorites_only` (optional): Return only favorited items

**Returns:** List of media items with metadata

**Example:**
```yaml
service: media_index.get_random_items
data:
  count: 20
  file_type: image
  favorites_only: true
```

### `media_index.get_file_metadata`

Get detailed metadata for a specific file.

**Parameters:**
- `file_path` (required): Full path to media file

**Returns:** Complete metadata including EXIF, location, and ratings

## File Management Services

### `media_index.mark_favorite`

Mark a file as favorite (writes to database and EXIF).

**Parameters:**
- `file_path` (required): Full path to media file
- `is_favorite` (optional, default: true): Favorite status

**Example:**
```yaml
service: media_index.mark_favorite
data:
  file_path: /media/photo/PhotoLibrary/sunset.jpg
  is_favorite: true
```

### `media_index.delete_media`

Delete a media file (moves to `_Junk` folder).

**Parameters:**
- `file_path` (required): Full path to media file

### `media_index.mark_for_edit`

Mark a file for editing (moves to `_Edit` folder).

**Parameters:**
- `file_path` (required): Full path to media file

## Maintenance Services

### `media_index.scan_folder`

Trigger a manual scan of media folders.

**Parameters:**
- `folder_path` (optional): Specific folder to scan (defaults to all watched folders)
- `force_rescan` (optional, default: false): Re-extract metadata for existing files

### `media_index.geocode_file`

Force geocoding of a file's GPS coordinates.

**Parameters:**
- `file_path` (required): Full path to media file

## Service Usage with Media Card

The Media Index services integrate seamlessly with the [Home Assistant Media Card](https://github.com/markaggar/ha-media-card):

- **`get_random_items`** - Used automatically by Media Card for slideshow content
- **`mark_favorite`** - Called when clicking favorite button on Media Card
- **`delete_media`** - Called when clicking delete button on Media Card  
- **`mark_for_edit`** - Called when clicking edit button on Media Card
- **`restore_edited_files`** - Run periodically to restore edited files