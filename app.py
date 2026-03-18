import base64
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ─── Language name → Translator code mapping ───
LANG_MAP = {
    "english": "en", "hindi": "hi", "spanish": "es", "french": "fr",
    "german": "de", "italian": "it", "portuguese": "pt", "russian": "ru",
    "japanese": "ja", "korean": "ko", "chinese": "zh-Hans", "arabic": "ar",
    "turkish": "tr", "dutch": "nl", "polish": "pl", "thai": "th",
    "vietnamese": "vi", "indonesian": "id", "malay": "ms", "tamil": "ta",
    "telugu": "te", "bengali": "bn", "marathi": "mr", "gujarati": "gu",
    "kannada": "kn", "malayalam": "ml", "punjabi": "pa", "urdu": "ur",
    "swedish": "sv", "norwegian": "nb", "danish": "da", "finnish": "fi",
    "greek": "el", "czech": "cs", "romanian": "ro", "hungarian": "hu",
    "ukrainian": "uk", "hebrew": "he", "persian": "fa", "swahili": "sw",
    "nepali": "ne", "sinhala": "si", "burmese": "my", "khmer": "km",
    "filipino": "fil", "catalan": "ca", "serbian": "sr-Cyrl",
    "croatian": "hr", "slovak": "sk", "slovenian": "sl", "bulgarian": "bg",
    "estonian": "et", "latvian": "lv", "lithuanian": "lt",
}

def get_lang_code(lang_name):
    """Convert a language name to its translator code."""
    code = LANG_MAP.get(lang_name.strip().lower())
    if code:
        return code
    # If user typed a code directly (e.g. "hi", "es"), use it
    if len(lang_name.strip()) <= 10:
        return lang_name.strip().lower()
    return "en"


@app.route("/")
def index():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Error: index.html not found.", 404


@app.route("/api/analyze", methods=["POST"])
def analyze_image():
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image uploaded"}), 400

    image_file = request.files["image"]
    target_language = request.form.get("language", "English")
    vision_endpoint = request.form.get("vision_endpoint", "").strip().rstrip("/")
    vision_key = request.form.get("vision_key", "").strip()
    translator_key = request.form.get("translator_key", "").strip()
    translator_region = request.form.get("translator_region", "").strip()

    if not vision_endpoint or not vision_key:
        return jsonify({"success": False, "error": "Azure Vision endpoint and key are required."}), 400
    if not translator_key or not translator_region:
        return jsonify({"success": False, "error": "Azure Translator key and region are required."}), 400
    if image_file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400

    try:
        image_bytes = image_file.read()

        # ──────────────────────────────────────────────
        # STEP 1: Azure Computer Vision — Analyze Image
        # ──────────────────────────────────────────────
        vision_url = f"{vision_endpoint}/vision/v3.2/analyze"
        vision_params = {
            "visualFeatures": "Description,Tags,Objects,Categories",
            "details": "Landmarks",
            "language": "en"
        }
        vision_headers = {
            "Ocp-Apim-Subscription-Key": vision_key,
            "Content-Type": "application/octet-stream"
        }

        vision_resp = requests.post(vision_url, headers=vision_headers, params=vision_params, data=image_bytes)
        vision_resp.raise_for_status()
        vision_data = vision_resp.json()

        # Extract useful info
        # Description
        captions = vision_data.get("description", {}).get("captions", [])
        description = captions[0]["text"] if captions else "an interesting location"
        confidence = round(captions[0]["confidence"] * 100, 1) if captions else 0

        # Tags
        tags = [t["name"] for t in vision_data.get("tags", []) if t.get("confidence", 0) > 0.5]

        # Landmarks (from categories → detail)
        landmarks = []
        for cat in vision_data.get("categories", []):
            if "detail" in cat and "landmarks" in cat["detail"]:
                for lm in cat["detail"]["landmarks"]:
                    if lm.get("confidence", 0) > 0.3:
                        landmarks.append(lm["name"])

        # Objects
        objects = list(set([obj["object"] for obj in vision_data.get("objects", [])]))

        # ──────────────────────────────────────────────
        # STEP 2: Build a Travel Guide in English
        # ──────────────────────────────────────────────
        place_name = landmarks[0] if landmarks else "the detected location"
        extra_landmarks = landmarks[1:] if len(landmarks) > 1 else []

        guide_text = f"# 🌍 Travel Guide: {place_name.title()}\n\n"
        guide_text += f"## 📸 Image Analysis\n"
        guide_text += f"**What we see:** {description.capitalize()} (confidence: {confidence}%)\n\n"

        if landmarks:
            guide_text += f"**Landmark(s) Detected:** {', '.join(landmarks)}\n\n"

        if tags:
            guide_text += f"**Scene Tags:** {', '.join(tags[:12])}\n\n"

        if objects:
            guide_text += f"**Objects Identified:** {', '.join(objects[:8])}\n\n"

        guide_text += "---\n\n"
        guide_text += f"## ✨ About {place_name.title()}\n"
        guide_text += f"This appears to be **{place_name.title()}**. "
        guide_text += f"The image shows {description}. "
        if tags:
            guide_text += f"The scene is characterized by elements such as {', '.join(tags[:5])}. "
        guide_text += "\n\n"

        guide_text += "---\n\n"
        guide_text += f"## 🗺️ Suggested Travel Plan for {place_name.title()}\n\n"

        guide_text += "### Day 1: Arrival & Exploration\n"
        guide_text += f"- **Morning:** Arrive and check into a nearby hotel. Take some time to rest.\n"
        guide_text += f"- **Afternoon:** Visit **{place_name.title()}** and explore the surroundings. "
        if tags and any(t in tags for t in ["outdoor", "nature", "mountain", "sky", "tree", "water", "beach"]):
            guide_text += "Enjoy the natural beauty and take stunning photographs.\n"
        else:
            guide_text += "Walk around and soak in the local atmosphere.\n"
        guide_text += f"- **Evening:** Try local cuisine at a nearby restaurant. Explore the night scene.\n\n"

        guide_text += "### Day 2: Deep Dive & Culture\n"
        guide_text += f"- **Morning:** Take a guided tour of {place_name.title()} to learn its history and significance.\n"
        if extra_landmarks:
            guide_text += f"- **Afternoon:** Visit nearby attractions: {', '.join(extra_landmarks)}.\n"
        else:
            guide_text += f"- **Afternoon:** Explore nearby attractions, museums, and cultural spots.\n"
        guide_text += f"- **Evening:** Pick up local souvenirs and enjoy a sunset view.\n\n"

        guide_text += "### Day 3: Adventure & Departure\n"
        if any(t in tags for t in ["outdoor", "nature", "mountain", "water", "beach", "hill"]):
            guide_text += f"- **Morning:** Go for a nature walk, hike, or water activity near {place_name.title()}.\n"
        else:
            guide_text += f"- **Morning:** Revisit your favorite spots or explore hidden gems around {place_name.title()}.\n"
        guide_text += f"- **Afternoon:** Relax, do some last-minute exploring, and prepare to depart.\n"
        guide_text += f"- **Evening:** Head to the airport/station with wonderful memories!\n\n"

        guide_text += "---\n\n"
        guide_text += "## 💡 Travel Tips\n"
        guide_text += f"- **Best time to visit:** Check the local weather and seasonal events.\n"
        guide_text += f"- **Getting there:** Look for flights or trains to the nearest city.\n"
        guide_text += f"- **What to pack:** Comfortable shoes, camera, sunscreen, and a good spirit!\n"
        guide_text += f"- **Safety:** Always keep your belongings safe and stay aware of your surroundings.\n"
        guide_text += f"- **Local etiquette:** Respect local customs and traditions.\n"

        # ──────────────────────────────────────────────
        # STEP 3: Azure Translator — Translate to User's Language
        # ──────────────────────────────────────────────
        lang_code = get_lang_code(target_language)

        if lang_code == "en":
            # No translation needed
            final_text = guide_text
        else:
            translator_url = "https://api.cognitive.microsofttranslator.com/translate"
            translator_params = {
                "api-version": "3.0",
                "to": lang_code
            }
            translator_headers = {
                "Ocp-Apim-Subscription-Key": translator_key,
                "Ocp-Apim-Subscription-Region": translator_region,
                "Content-Type": "application/json"
            }

            # Split text into chunks (Translator API has 10000 char limit per element)
            chunks = []
            current_chunk = ""
            for line in guide_text.split("\n"):
                if len(current_chunk) + len(line) + 1 > 9000:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"
            if current_chunk:
                chunks.append(current_chunk)

            translated_parts = []
            for chunk in chunks:
                body = [{"Text": chunk}]
                t_resp = requests.post(translator_url, headers=translator_headers, params=translator_params, json=body)
                t_resp.raise_for_status()
                t_data = t_resp.json()
                translated_parts.append(t_data[0]["translations"][0]["text"])

            final_text = "".join(translated_parts)

        return jsonify({"success": True, "result": final_text})

    except requests.exceptions.HTTPError as e:
        error_detail = str(e)
        try:
            error_detail += " | " + e.response.text
        except:
            pass
        return jsonify({"success": False, "error": error_detail}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("Starting SR24+ AI Travel Guide Backend...")
    app.run(debug=True, port=5000)
