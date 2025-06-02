# Create this file: create_logos.py (run once to generate placeholder logos)

from PIL import Image, ImageDraw, ImageFont
import os

def create_university_logo(text, color, filename, size=(100, 100)):
    """Create a simple text-based logo"""
    # Create image with transparent background
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default
    try:
        font = ImageFont.truetype("Arial.ttf", 36)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)  # macOS
        except:
            font = ImageFont.load_default()
    
    # Calculate text position to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Draw background circle
    margin = 10
    draw.ellipse([margin, margin, size[0]-margin, size[1]-margin], fill=color)
    
    # Draw text
    draw.text((x, y), text, fill='white', font=font)
    
    return img

def main():
    # Create directory
    logo_dir = "static/resume/logos"
    os.makedirs(logo_dir, exist_ok=True)
    
    # University logos data
    universities = [
        ("Harvard", "H", "#A41E22"),
        ("MIT", "MIT", "#8A8B8C"), 
        ("Cambridge", "CAM", "#003B5C"),
        ("Stanford", "S", "#8C1515"),
        ("Wharton", "W", "#011F5B"),
        ("Berkeley", "UC", "#003262")
    ]
    
    for name, text, color in universities:
        img = create_university_logo(text, color, f"{name}.png")
        img.save(f"{logo_dir}/{name}.png", "PNG")
        print(f"Created {name}.png")

if __name__ == "__main__":
    main()