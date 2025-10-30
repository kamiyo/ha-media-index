#!/usr/bin/env python3
"""Test MP4 rating write with mutagen."""
import sys
from pathlib import Path

# Test file
TEST_FILE = "/media/Photo/PhotoLibrary/New/back puzzle.mp4"

print(f"Testing MP4 rating write on: {TEST_FILE}")
print("=" * 60)

try:
    from mutagen.mp4 import MP4, MP4FreeForm
    
    # Read current tags
    print("\n1. Reading current tags...")
    video = MP4(TEST_FILE)
    print(f"   Current tags: {list(video.keys())}")
    if '----:com.apple.iTunes:rating' in video:
        print(f"   Current rating: {video['----:com.apple.iTunes:rating']}")
    else:
        print("   No rating tag found")
    
    # Write rating
    print("\n2. Writing rating=5...")
    rating = 5
    video['----:com.apple.iTunes:rating'] = [
        MP4FreeForm(str(rating).encode('utf-8'), dataformat=1)
    ]
    print(f"   Tag set in memory: {video['----:com.apple.iTunes:rating']}")
    
    # Save
    print("\n3. Calling video.save()...")
    video.save()
    print("   save() completed without exception")
    
    # Verify by re-reading
    print("\n4. Verifying by re-reading file...")
    video_verify = MP4(TEST_FILE)
    print(f"   Tags after save: {list(video_verify.keys())}")
    if '----:com.apple.iTunes:rating' in video_verify:
        raw_value = video_verify['----:com.apple.iTunes:rating']
        print(f"   ✅ Rating tag FOUND: {raw_value}")
        print(f"   Raw bytes: {raw_value[0] if raw_value else 'None'}")
        if raw_value and len(raw_value) > 0:
            decoded = raw_value[0].decode('utf-8') if isinstance(raw_value[0], bytes) else str(raw_value[0])
            print(f"   Decoded value: {decoded}")
    else:
        print("   ❌ Rating tag NOT FOUND after save - WRITE FAILED")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
