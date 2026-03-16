import os
import shutil
import glob
import random
import json

# Source and Dest paths
src_base = r"c:\Users\User\Desktop\Senyas Web\Sign Language model\datasets\FSL_Final"
dest_base = r"c:\Users\User\Desktop\Senyas Web\website\static\images\signs"

# Clean destination first (optional, but good to avoid stale single images)
# But let's just overwrite.

if not os.path.exists(dest_base):
    os.makedirs(dest_base)

letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
sign_counts = {}

for char in letters:
    src_dir = os.path.join(src_base, char)
    
    if not os.path.exists(src_dir):
        print(f"Warning: Source directory for {char} not found: {src_dir}")
        sign_counts[char] = 0
        continue

    # Find all candidates
    candidates = []
    # recursive=True might be overkill given structure, but let's just look in top level
    # matching the previous dir output
    for f in os.listdir(src_dir):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            candidates.append(os.path.join(src_dir, f))
    
    # Shuffle and pick top 10
    random.shuffle(candidates)
    selected = candidates[:10]
    
    sign_counts[char] = len(selected)
    
    if not selected:
        print(f"Warning: No images found for {char}")
        continue
        
    print(f"Copying {len(selected)} images for {char}...")
    
    for idx, src_file in enumerate(selected, 1):
        # Dest name: A_1.jpg, A_2.jpg
        # Normalized to lowercase extension .jpg for simplicity
        dest_filename = f"{char}_{idx}.jpg"
        dest_file = os.path.join(dest_base, dest_filename)
        
        try:
            shutil.copy2(src_file, dest_file)
        except Exception as e:
            print(f"Error copying {src_file}: {e}")

# Save counts to JSON for frontend usage
manifest_path = os.path.join(dest_base, "sign_counts.json")
with open(manifest_path, 'w') as f:
    json.dump(sign_counts, f)

print("Done. Counts saved to sign_counts.json")
print(sign_counts)

