"""
Level 1: Evidence Generator

This module generates crash site evidence (soil sample, flora video, star field)
based on your coordinates. The evidence characteristics match your biome,
which the ADK agent will later analyze to deduce your location.

Run this at the start of Level 1 to create your personalized evidence.
"""

import os
import sys
import json
import io
import time
import requests
from PIL import Image

from google import genai
from google.genai import types

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_PATH = "../config.json"
OUTPUTS_DIR = "outputs"

# =============================================================================
# LEVEL GATE CHECK
# =============================================================================
# Level 1 requires Level 0 completion. This checks for the necessary state.

if not os.path.exists(CONFIG_PATH):
    print("❌ config.json not found!")
    print("   Please complete Level 0 first.")
    print("   See: https://codelabs.developers.google.com/way-back-home-level-0/instructions")
    sys.exit(1)

with open(CONFIG_PATH) as f:
    config = json.load(f)

required_fields = ["participant_id", "starting_x", "starting_y", "username", "api_base"]
missing = [f for f in required_fields if f not in config]

if missing:
    print(f"❌ Missing required config fields: {missing}")
    print("   Please complete Level 0 first.")
    sys.exit(1)

# Extract configuration
USERNAME = config["username"]
PARTICIPANT_ID = config["participant_id"]
X = config["starting_x"]
Y = config["starting_y"]
API_BASE = config["api_base"]

print(f"✓ Welcome back, {USERNAME}!")
print(f"  Coordinates: ({X}, {Y})")
print(f"  Ready to analyze your crash site.\n")

# =============================================================================
# BIOME MAPPING
# =============================================================================


def get_biome(x: int, y: int) -> str:
    """
    Map coordinates to biome.

    The planet is divided into 4 quadrants, each with a distinct biome:
    - Northwest (x < 50, y >= 50): CRYO
    - Northeast (x >= 50, y >= 50): VOLCANIC
    - Southwest (x < 50, y < 50): BIOLUMINESCENT
    - Southeast (x >= 50, y < 50): FOSSILIZED
    """
    if x < 50 and y >= 50:
        return "CRYO"
    elif x >= 50 and y >= 50:
        return "VOLCANIC"
    elif x < 50 and y < 50:
        return "BIOLUMINESCENT"
    else:
        return "FOSSILIZED"


# =============================================================================
# BIOME EVIDENCE PROMPTS
# =============================================================================
# Each biome has distinct characteristics that will be reflected in the
# generated evidence. The AI analysis tools will later identify these
# characteristics to deduce the biome.

BIOME_EVIDENCE = {
    "CRYO": {
        "soil_prompt": """Create a close-up photograph of an alien soil sample from a frozen world.

CRITICAL VISUAL REQUIREMENTS:
- Frozen methane ice crystals embedded in pale blue-white soil
- Crystalline formations with sharp geometric structures
- Frost patterns and ice veins running through the sample
- Cold color palette: ice blue, white, pale silver, hints of cyan
- Glistening, reflective surfaces suggesting extreme cold
- Some darker rocky material visible beneath the ice layer

STYLE:
- Scientific specimen photography style
- Macro close-up, detailed textures visible
- Soft diffused lighting to show ice transparency
- Clean composition, sample fills most of frame
- Photorealistic but clearly alien/otherworldly

This is evidence from a crash site on a frozen alien world.""",

        "flora_prompt": """Create a short video clip of alien flora in a frozen environment.

VISUAL REQUIREMENTS:
- Crystalline frost ferns with delicate ice-like fronds
- Plants that appear made of living ice, semi-transparent
- Gentle swaying motion as if in cold wind
- Occasional ice particles or snow drifting past
- Color palette: ice blue, white, pale cyan, silver
- Bioluminescent blue glow from within some plants
- Frozen landscape visible in background

AUDIO REQUIREMENTS:
- Howling cold wind, hollow and resonant
- Crystalline chiming sounds as ice plants move
- Crackling ice sounds, subtle
- Ethereal, cold atmosphere
- No warm or organic sounds

STYLE:
- Dreamy, ethereal, beautiful but harsh
- Slow, contemplative movement

This is flora from a frozen alien biome.""",

        "star_prompt": """Create a night sky photograph from a frozen alien planet.

CRITICAL VISUAL REQUIREMENTS:
- Dominant blue giant star, very large and bright, blue-white color
- Ice-blue nebula stretching across part of the sky
- Stars with a cold color temperature (white, blue)
- Wispy aurora-like formations in cyan and white
- Dark sky contrasting with bright stellar objects
- Perhaps distant ice formations silhouetted at bottom edge

STYLE:
- Astrophotography style, deep space feel
- Rich detail in nebula and star field
- Cold, crystalline beauty
- Awe-inspiring but harsh

This is the night sky from a frozen alien world's surface."""
    },

    "VOLCANIC": {
        "soil_prompt": """Create a close-up photograph of an alien soil sample from a volcanic world.

CRITICAL VISUAL REQUIREMENTS:
- Black obsidian chunks and volcanic glass
- Veins of cooling magma, glowing orange-red
-ite formations andite rocky structures
- Dark charred soil with ember-like particles
- Color palette: black, deep red, orange, glowing yellow
- Heat shimmer effect on some surfaces
- Crystallized lava formations

STYLE:
- Scientific specimen photography style
- Macro close-up, detailed textures visible
- Dramatic lighting suggesting internal heat
- Clean composition, sample fills most of frame
- Photorealistic but clearly alien/otherworldly

This is evidence from a crash site on a volcanic alien world.""",

        "flora_prompt": """Create a short video clip of alien flora in a volcanic environment.

VISUAL REQUIREMENTS:
- Fire blooms: flowers that seem made of flame, petals like fire
- Heat-resistant plants with dark, armored surfaces
- Ember-like spores or particles floating upward
- Plants that glow from within with orange-red light
- Color palette: black, deep red, orange, yellow flames
- Heat distortion/shimmer in the air
- Volcanic landscape visible in background, maybe distant lava

AUDIO REQUIREMENTS:
- Deep rumbling, volcanic activity
- Crackling fire sounds
- Hissing steam vents
- Occasional distant explosions or eruptions
- Warm, intense atmospheric sounds

STYLE:
- Dramatic, intense, dangerous beauty
- Dynamic movement from heat currents

This is flora from a volcanic alien biome.""",

        "star_prompt": """Create a night sky photograph from a volcanic alien planet.

CRITICAL VISUAL REQUIREMENTS:
- Red dwarf binary star system - two reddish stars close together
- Orange and red nebula dominating part of the sky
- Warm color temperature throughout (red, orange, yellow stars)
- Smoke or ash particles in the atmosphere creating haze
- Distant volcanic glow on the horizon
- Stars appear to flicker through the heated atmosphere

STYLE:
- Astrophotography style with atmospheric effects
- Warm, intense colors
- Dramatic and foreboding
- Heat distortion effects

This is the night sky from a volcanic alien world's surface."""
    },

    "BIOLUMINESCENT": {
        "soil_prompt": """Create a close-up photograph of an alien soil sample from a bioluminescent world.

CRITICAL VISUAL REQUIREMENTS:
- Phosphorescent minerals that glow purple and green
- Organic luminescent material mixed with soil
- Glowing veins running through darker earth
- Mushroom-like growths with internal light
- Color palette: deep purple, electric green, cyan glow, dark earth
- Particles that emit soft light
- Wet, organic texture suggesting rich biology

STYLE:
- Scientific specimen photography style
- Macro close-up, detailed textures visible
- Lighting that shows the bioluminescence clearly
- Clean composition, sample fills most of frame
- Photorealistic but clearly alien/otherworldly

This is evidence from a crash site on a bioluminescent alien world.""",

        "flora_prompt": """Create a short video clip of alien flora in a bioluminescent environment.

VISUAL REQUIREMENTS:
- Glowing fungi clusters pulsing with soft light
- Bioluminescent plants in purple, green, and cyan
- Floating luminescent spores drifting through air
- Plants that pulse rhythmically, like breathing
- Color palette: deep purple, electric green, cyan, soft pink glow
- Dark environment lit only by the organisms
- Ethereal, dreamlike atmosphere

AUDIO REQUIREMENTS:
- Deep crystalline humming, resonant
- Soft chiming sounds, like glass wind chimes
- Gentle pulsing tones matching the light rhythm
- Ethereal, otherworldly ambient sounds
- Peaceful but alien atmosphere

STYLE:
- Dreamy, magical, bioluminescent beauty
- Slow pulsing movements, hypnotic

This is flora from a bioluminescent alien biome.""",

        "star_prompt": """Create a night sky photograph from a bioluminescent alien planet.

CRITICAL VISUAL REQUIREMENTS:
- Green pulsar star visible, with rhythmic brightness variation
- Purple and magenta nebula swirling in the sky
- Stars in unusual colors (green, purple, cyan)
- Bioluminescent glow from the ground illuminating lower sky
- Ethereal, dreamlike quality
- Perhaps luminescent clouds or atmospheric organisms

STYLE:
- Astrophotography style with fantasy elements
- Rich purples, greens, and cyans
- Magical and mysterious
- Soft, glowing quality throughout

This is the night sky from a bioluminescent alien world's surface."""
    },

    "FOSSILIZED": {
        "soil_prompt": """Create a close-up photograph of an alien soil sample from an ancient fossilized world.

CRITICAL VISUAL REQUIREMENTS:
- Amber deposits with preserved ancient matter inside
- Fossilized remains of unknown organisms
- Golden and brown crystalline formations
- Ancient petrified organic material
- Color palette: amber, gold, deep brown, cream, bronze
- Layered sedimentary patterns showing age
- Jewel-like quality to the amber sections

STYLE:
- Scientific specimen photography style
- Macro close-up, detailed textures visible
- Warm lighting enhancing golden tones
- Clean composition, sample fills most of frame
- Photorealistic but clearly alien/otherworldly

This is evidence from a crash site on an ancient fossilized alien world.""",

        "flora_prompt": """Create a short video clip of alien flora in a fossilized/ancient environment.

VISUAL REQUIREMENTS:
- Petrified spiral trees, partially crystallized
- Ancient plants that move very slowly, almost frozen in time
- Amber-like sap dripping in slow motion
- Plants with golden, bronze, and brown coloring
- Some living growth on ancient petrified structures
- Dust motes floating in golden light
- Ancient, preserved landscape

AUDIO REQUIREMENTS:
- Deep resonant tones, ancient and slow
- Crystalline sounds, mineral-like
- Slow creaking of ancient growth
- Wind through petrified forests
- Timeless, eternal atmosphere

STYLE:
- Ancient, preserved, timeless beauty
- Very slow movements suggesting geological time

This is flora from an ancient fossilized alien biome.""",

        "star_prompt": """Create a night sky photograph from an ancient fossilized alien planet.

CRITICAL VISUAL REQUIREMENTS:
- Yellow sun-like star, stable and warm
- Golden nebula with ancient, stable formations
- Stars in warm colors (yellow, gold, amber)
- Clear, stable atmosphere with excellent visibility
- Ancient, unchanging quality to the sky
- Perhaps visible rings or old planetary debris

STYLE:
- Astrophotography style, classical beauty
- Warm golden and amber tones
- Timeless and eternal feeling
- Peaceful and stable

This is the night sky from an ancient fossilized alien world's surface."""
    }
}


# =============================================================================
# GEMINI CLIENT INITIALIZATION
# =============================================================================

client = genai.Client(
    vertexai=True,
    project=os.environ.get("GOOGLE_CLOUD_PROJECT", config.get("project_id")),
    location="us-central1"
)


# =============================================================================
# EVIDENCE GENERATION FUNCTIONS
# =============================================================================


def generate_images(biome: str) -> dict:
    """
    Generate soil sample and star field images using Gemini Flash Image.

    Uses a chat session to maintain style consistency between images,
    following the same pattern as Level 0 avatar generation.

    Args:
        biome: The biome type (CRYO, VOLCANIC, BIOLUMINESCENT, FOSSILIZED)

    Returns:
        dict with soil_path and star_path
    """
    prompts = BIOME_EVIDENCE[biome]

    # Create chat session for style consistency
    chat = client.chats.create(
        model="gemini-2.5-flash-image",
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"]
        )
    )

    # Generate soil sample
    print("🔬 Generating soil sample...")
    soil_response = chat.send_message(prompts["soil_prompt"])

    soil_path = None
    for part in soil_response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            soil_image = Image.open(io.BytesIO(image_bytes))
            soil_path = os.path.join(OUTPUTS_DIR, "soil_sample.png")
            soil_image.save(soil_path)
            break

    if soil_path is None:
        raise Exception("Failed to generate soil sample - no image in response")

    print(f"✓ Soil sample captured: {soil_path}")

    # Generate star field (same chat session for style consistency)
    print("✨ Capturing star field...")
    star_response = chat.send_message(prompts["star_prompt"])

    star_path = None
    for part in star_response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            star_image = Image.open(io.BytesIO(image_bytes))
            star_path = os.path.join(OUTPUTS_DIR, "star_field.png")
            star_image.save(star_path)
            break

    if star_path is None:
        raise Exception("Failed to generate star field - no image in response")

    print(f"✓ Star field captured: {star_path}")

    return {
        "soil_path": soil_path,
        "star_path": star_path
    }


def generate_flora_video(biome: str) -> str:
    """
    Generate flora video with audio using Veo 3.1.

    This creates a short video clip showing alien flora with
    synchronized ambient audio that matches the biome characteristics.
    Veo 3.1 natively generates both video and audio together.

    Args:
        biome: The biome type (CRYO, VOLCANIC, BIOLUMINESCENT, FOSSILIZED)

    Returns:
        Path to the generated video file
    """
    prompts = BIOME_EVIDENCE[biome]

    print("🌿 Recording flora activity...")
    print("   (This may take 1-2 minutes for video generation)")

    # Generate video with Veo 3.1 (includes native audio generation)
    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=prompts["flora_prompt"],
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            resolution="720p",
            duration_seconds=4,
        )
    )

    # Poll until video generation is complete (typically 1-2 minutes)
    while not operation.done:
        print("   Generating video...")
        time.sleep(10)
        operation = client.operations.get(operation)

    # Check for errors
    if not operation.response or not operation.response.generated_videos:
        raise Exception("Failed to generate flora video - no video in response")

    # Save the video directly (Vertex AI returns video bytes inline)
    generated_video = operation.response.generated_videos[0]
    flora_path = os.path.join(OUTPUTS_DIR, "flora_recording.mp4")
    generated_video.video.save(flora_path)

    print(f"✓ Flora recorded: {flora_path}")

    return flora_path


def upload_evidence(local_paths: dict) -> dict:
    """
    Upload evidence files to Mission Control via backend API.

    This follows the same pattern as Level 0's avatar upload,
    using the backend API to store files in Firebase Storage.

    Args:
        local_paths: dict with paths to local evidence files

    Returns:
        dict with Cloud Storage URLs for evidence files
    """
    url = f"{API_BASE}/participants/{PARTICIPANT_ID}/evidence"

    try:
        with open(local_paths["soil_path"], "rb") as soil, \
             open(local_paths["star_path"], "rb") as stars, \
             open(local_paths["flora_path"], "rb") as flora:

            # Determine content type for flora
            flora_content_type = "image/png"
            if local_paths["flora_path"].endswith(".mp4"):
                flora_content_type = "video/mp4"

            files = {
                "soil_sample": ("soil_sample.png", soil, "image/png"),
                "star_field": ("star_field.png", stars, "image/png"),
                "flora_recording": (os.path.basename(local_paths["flora_path"]), flora, flora_content_type),
            }

            response = requests.post(url, files=files, timeout=120)

        response.raise_for_status()
        return response.json()["evidence_urls"]

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to upload evidence: {e}")
        raise


def update_config_with_evidence(urls: dict):
    """
    Update config.json with evidence URLs for the agent to use.

    Args:
        urls: dict with Cloud Storage URLs for evidence files
    """
    config["evidence_urls"] = urls
    config["biome_generated"] = get_biome(X, Y)  # Store for verification

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print("✓ Config updated with evidence URLs")


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main():
    """Generate all crash site evidence."""

    # Create outputs directory
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    # Determine biome from coordinates
    biome = get_biome(X, Y)
    print("📍 Crash site analysis initiated...")
    print("   Generating evidence for your location...\n")

    # Generate evidence
    image_paths = generate_images(biome)
    flora_path = generate_flora_video(biome)

    # Combine all paths
    all_paths = {
        "soil_path": image_paths["soil_path"],
        "star_path": image_paths["star_path"],
        "flora_path": flora_path
    }

    # Upload to Mission Control (via backend API)
    print("\n📤 Uploading evidence to Mission Control...")
    urls = upload_evidence(all_paths)

    # Update config
    update_config_with_evidence(urls)

    print("\n" + "=" * 50)
    print("✅ Evidence generation complete!")
    print("=" * 50)
    print("\nYour crash site evidence is ready for analysis.")
    print("Evidence files saved in: outputs/")
    print("\nNext step: Build the MCP analysis tools")
    print("Continue with the codelab instructions")


if __name__ == "__main__":
    main()
