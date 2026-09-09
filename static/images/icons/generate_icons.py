from PIL import Image, ImageDraw, ImageFont
import os

# Icon sizes needed for PWA
sizes = [72, 96, 128, 144, 152, 192, 384, 512]

# Colors
PRIMARY = '#3B2E92'      # Genesis Indigo
SECONDARY = '#F59E0B'    # Genesis Amber
BACKGROUND = '#0F172A'   # Genesis Sidebar

print("🎨 Generating PWA icons...")
print("📁 Location: static/images/icons/")
print("=" * 50)

for size in sizes:
    # Create a new image with dark background
    img = Image.new('RGB', (size, size), BACKGROUND)
    draw = ImageDraw.Draw(img)
    
    # Draw a rounded rectangle background
    margin = size // 10
    corner_radius = size // 8
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=corner_radius,
        fill=PRIMARY,
        outline=SECONDARY,
        width=max(2, size // 40)
    )
    
    # Draw the text "GS"
    try:
        # Try to use a system font
        font_size = size // 3
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
        font_size = size // 4
    
    text = "GS"
    
    # Center the text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 5
    
    # Draw the text
    draw.text((x, y), text, font=font, fill='#FFFFFF')
    
    # Save the icon
    icon_path = f'icon-{size}x{size}.png'
    img.save(icon_path)
    print(f'✅ Created icon-{size}x{size}.png')

print("=" * 50)
print("🎉 All icons generated successfully!")