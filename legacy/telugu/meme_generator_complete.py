#!/usr/bin/env python3
"""
COMPLETE MEME GENERATOR - Step by Step
Generates Telugu/Hindi memes with labeled reaction images
Run this in your MemeFactory folder
"""

import os
import sys
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ========== STEP 1: SET UP PATHS ==========
print("\n" + "="*70)
print("STEP 1: SETTING UP PATHS")
print("="*70)

MEMEFACTORY_PATH = r"C:\Users\ASUS\Documents\MemeFactory"
REACTION_IMAGES_PATH = os.path.join(MEMEFACTORY_PATH, "assets", "Reaction images")
OUTPUT_PATH = os.path.join(MEMEFACTORY_PATH, "Generated_Memes")

print(f"✓ MemeFactory base: {MEMEFACTORY_PATH}")
print(f"✓ Reaction images: {REACTION_IMAGES_PATH}")
print(f"✓ Output folder: {OUTPUT_PATH}")

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_PATH, exist_ok=True)
print(f"✓ Output folder ready")


# ========== STEP 2: TODAY'S MEME CONTENT ==========
print("\n" + "="*70)
print("STEP 2: DEFINING MEME CONTENT")
print("="*70)

MEME_DATA = {
    "top_text": "Peddi Day 5 boxoffice report chudagane 📊",
    "emotion_needed": "skeptical",  # What emotion we need
    "news_source": "Ram Charan Peddi - Day 5 box office underperformed",
}

print(f"✓ Top text: {MEME_DATA['top_text']}")
print(f"✓ Emotion needed: {MEME_DATA['emotion_needed']}")


# ========== STEP 3: SCAN REACTION IMAGES ==========
print("\n" + "="*70)
print("STEP 3: SCANNING REACTION IMAGES BY EMOTION")
print("="*70)

def scan_reaction_images(reaction_folder):
    """
    Scan the reaction folder and organize images by emotion label
    Expected format: images have emotion names in filename or are in subfolders
    """
    emotion_map = {}
    
    if not os.path.exists(reaction_folder):
        print(f"❌ Reaction folder not found: {reaction_folder}")
        return None
    
    # Get all image files
    all_files = []
    for root, dirs, files in os.walk(reaction_folder):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(root, file)
                all_files.append((file, full_path))
    
    print(f"✓ Found {len(all_files)} reaction images total")
    
    # Organize by emotion (look for emotion keywords in filename)
    emotions = ["skeptical", "shocked", "thinking", "laughing", "angry",
                "disappointed", "savage", "proud", "confused", "sarcastic",
                "crying", "serious", "disgusted", "pointing", "swagger"]

    # Emotions not directly present in filenames map to the closest available label
    emotion_synonyms = {
        "skeptical": "sarcastic",
    }
    
    for emotion in emotions:
        matching = [(name, path) for name, path in all_files 
                   if emotion.lower() in name.lower()]
        if matching:
            emotion_map[emotion] = matching
            print(f"  • {emotion}: {len(matching)} images")

    return emotion_map, all_files, emotion_synonyms


scan_result = scan_reaction_images(REACTION_IMAGES_PATH)

if scan_result is None:
    print("❌ Failed to scan reaction images. Exiting.")
    sys.exit(1)

emotion_map, all_images, emotion_synonyms = scan_result


# ========== STEP 4: PICK A REACTION IMAGE ==========
print("\n" + "="*70)
print("STEP 4: PICKING REACTION IMAGE FOR EMOTION")
print("="*70)

def pick_reaction_image(emotion_needed, emotion_map, all_images, emotion_synonyms):
    """
    Pick a reaction image matching the emotion.
    Falls back to a synonym emotion, then to random if neither is found.
    """
    if emotion_needed in emotion_map:
        chosen_name, chosen_path = random.choice(emotion_map[emotion_needed])
        print(f"✓ Found '{emotion_needed}' emotion")
        print(f"✓ Picked: {chosen_name}")
        return chosen_path

    synonym = emotion_synonyms.get(emotion_needed)
    if synonym and synonym in emotion_map:
        chosen_name, chosen_path = random.choice(emotion_map[synonym])
        print(f"⚠️  No '{emotion_needed}' images found, using synonym '{synonym}'")
        print(f"✓ Picked: {chosen_name}")
        return chosen_path

    print(f"⚠️  No '{emotion_needed}' images found")
    print(f"⚠️  Using random image instead")
    _, chosen_path = random.choice(all_images)
    print(f"✓ Picked: {os.path.basename(chosen_path)}")
    return chosen_path

reaction_image_path = pick_reaction_image(MEME_DATA["emotion_needed"], emotion_map, all_images, emotion_synonyms)


# ========== STEP 5: LOAD AND RESIZE REACTION IMAGE ==========
print("\n" + "="*70)
print("STEP 5: LOADING REACTION IMAGE")
print("="*70)

try:
    reaction_img = Image.open(reaction_image_path)
    print(f"✓ Loaded: {reaction_image_path}")
    print(f"✓ Original size: {reaction_img.size}")
except Exception as e:
    print(f"❌ Could not load image: {e}")
    sys.exit(1)


# ========== STEP 6: CREATE CANVAS ==========
print("\n" + "="*70)
print("STEP 6: CREATING INSTAGRAM CANVAS (1080x1350px)")
print("="*70)

INSTA_WIDTH = 1080
INSTA_HEIGHT = 1350
TOP_BAR_HEIGHT = 150
BOTTOM_BAR_HEIGHT = 150
REACTION_AREA_HEIGHT = INSTA_HEIGHT - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT

# Create black canvas
canvas = Image.new("RGB", (INSTA_WIDTH, INSTA_HEIGHT), color="black")
print(f"✓ Canvas created: {INSTA_WIDTH}x{INSTA_HEIGHT}px")

# Resize reaction image to fit in middle area
print(f"✓ Resizing reaction image to fit {INSTA_WIDTH}x{REACTION_AREA_HEIGHT}px area")
reaction_img.thumbnail((INSTA_WIDTH, REACTION_AREA_HEIGHT), Image.Resampling.LANCZOS)
print(f"✓ Resized to: {reaction_img.size}")

# Calculate position to center vertically in middle area
reaction_y = TOP_BAR_HEIGHT + (REACTION_AREA_HEIGHT - reaction_img.height) // 2
reaction_x = (INSTA_WIDTH - reaction_img.width) // 2

# Paste reaction image onto canvas
canvas.paste(reaction_img, (reaction_x, reaction_y))
print(f"✓ Pasted at position: ({reaction_x}, {reaction_y})")


# ========== STEP 7: PREPARE FONTS ==========
print("\n" + "="*70)
print("STEP 7: LOADING FONTS")
print("="*70)

def load_fonts():
    """Load fonts for text rendering"""
    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\impact.ttf", 60)
        caption_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 40)
        handle_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 32)
        print("✓ Loaded: Impact (title), Arial (caption), Arial (handle)")
        return title_font, caption_font, handle_font
    except OSError as e:
        print(f"⚠️  System fonts not found: {e}")
        print(f"⚠️  Using default font (limited rendering)")
        return ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()

title_font, caption_font, handle_font = load_fonts()


# ========== STEP 8: ADD TEXT OVERLAYS ==========
print("\n" + "="*70)
print("STEP 8: ADDING TEXT OVERLAYS")
print("="*70)

draw = ImageDraw.Draw(canvas)

# Create semi-transparent overlays for text readability
print("✓ Creating semi-transparent overlay bars...")

# Top bar overlay (for top text)
overlay_top = Image.new("RGBA", (INSTA_WIDTH, TOP_BAR_HEIGHT), (0, 0, 0, 200))
canvas.paste(overlay_top, (0, 0), overlay_top)
print(f"  • Top bar at y=0 to y={TOP_BAR_HEIGHT}")

# Recreate draw object after pasting overlay
draw = ImageDraw.Draw(canvas)
text_color = (255, 255, 255)  # White

import re
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+"
)

def strip_emoji(text):
    """Impact/Arial have no emoji glyphs, so drawing emoji renders as tofu boxes."""
    return EMOJI_PATTERN.sub("", text).strip()

# TOP TEXT (centered in top bar)
top_text_render = strip_emoji(MEME_DATA['top_text'])
print(f"\n✓ Rendering top text:")
print(f"  Text: {MEME_DATA['top_text']}")
bbox_top = draw.textbbox((0, 0), top_text_render, font=title_font)
text_width_top = bbox_top[2] - bbox_top[0]
top_x = (INSTA_WIDTH - text_width_top) // 2
top_y = 20
draw.text((top_x, top_y), top_text_render, fill=text_color, font=title_font)
print(f"  Position: ({top_x}, {top_y})")



# ========== STEP 9: SAVE MEME ==========
print("\n" + "="*70)
print("STEP 9: SAVING MEME")
print("="*70)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_filename = f"meme_peddi_{timestamp}.png"
output_path = os.path.join(OUTPUT_PATH, output_filename)

try:
    canvas.save(output_path, quality=95)
    print(f"✓ Saved: {output_path}")
    print(f"✓ File size: {os.path.getsize(output_path) / 1024:.1f} KB")
except Exception as e:
    print(f"❌ Failed to save: {e}")
    sys.exit(1)


# ========== STEP 10: SUMMARY ==========
print("\n" + "="*70)
print("STEP 10: SUMMARY & NEXT STEPS")
print("="*70)

print(f"""
✅ MEME CREATED SUCCESSFULLY!

📊 Meme Details:
   • Top text: {MEME_DATA['top_text']}
   • Reaction: {os.path.basename(reaction_image_path)}
   • Dimensions: 1080x1350px (Instagram optimized)
   • Format: PNG (high quality)

📁 File saved to:
   {output_path}

🎯 Next Steps:
   1. Open the meme in your browser/image viewer to verify it looks good
   2. Once you confirm, I can:
      - Build the NEWS SCRAPER to auto-fetch trending stories
      - Build the SCHEDULER to run at 8AM, 1PM, 9PM daily
      - Build the DRIVE UPLOADER to save memes automatically
      - Wire it all together for FULLY AUTOMATED daily memes

3. Eventually: Set up Meta Graph API for auto-posting to Instagram

Ready to automate the rest? Let me know! 🚀
""")

print("="*70)
