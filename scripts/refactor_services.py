"""Refactor __init__.py to support target selectors for multi-instance."""
import re

# Read the file
with open('custom_components/media_index/__init__.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all occurrences of service handlers that reference entry.entry_id
patterns = [
    (r'cache_manager = hass\.data\[DOMAIN\]\[entry\.entry_id\]\["cache_manager"\]',
     'entry_id = _get_entry_id_from_call(hass, call)\n        cache_manager = hass.data[DOMAIN][entry_id]["cache_manager"]'),
    
    (r'scanner = hass\.data\[DOMAIN\]\[entry\.entry_id\]\["scanner"\]',
     'entry_id = _get_entry_id_from_call(hass, call)\n        scanner = hass.data[DOMAIN][entry_id]["scanner"]'),
    
    (r'config = hass\.data\[DOMAIN\]\[entry\.entry_id\]\["config"\]',
     'config = hass.data[DOMAIN][entry_id]["config"]'),
    
    (r'geocode_service = hass\.data\[DOMAIN\]\[entry\.entry_id\]\.get\("geocode_service"\)',
     'geocode_service = hass.data[DOMAIN][entry_id].get("geocode_service")'),
]

# Apply replacements
for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

# Write back
with open('custom_components/media_index/__init__.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Refactoring complete!")
