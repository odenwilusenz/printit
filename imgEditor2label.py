from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import io, os

# Function to find .ttf fonts
def find_fonts():
    font_dirs = ["/usr/share/fonts/truetype", "~/.fonts"]
    fonts = []
    for dir in font_dirs:
        if os.path.exists(dir):
            for root, _, files in os.walk(dir):
                for file in files:
                    if file.endswith(".ttf"):
                        fonts.append(os.path.join(root, file))
    return fonts

# Streamlit UI
st.title("Custom Text to Image")


# Multiline Text Input
text = st.text_area("Enter your text", "Hello,\nWorld!")

col1, col2 = st.columns(2)


# Font Selection
with col1:
    available_fonts = find_fonts()
    font = st.selectbox("Choose your font", available_fonts)

with col2:
    # Alignment
    alignment_options = ["left", "center", "right"]
    alignment = st.selectbox("Choose text alignment", alignment_options, index=1)

# Font Size
font_size = st.slider("Font Size", 10, 200, 50)

# Calculate Image Height
num_lines = len(text.split('\n'))
image_height = num_lines * (font_size + 10)  # 10 is line spacing

# Create Image
img = Image.new("RGB", (696, image_height), color="white")
d = ImageDraw.Draw(img)
fnt = ImageFont.truetype(font, font_size)

# Draw Text
y = 0
for line in text.split('\n'):
    bbox = d.textbbox((0, y), line, font=fnt)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    if alignment == "center":
        x = (696 - text_width) // 2
    elif alignment == "right":
        x = 696 - text_width
    else:
        x = 0

    d.text((x, y), line, font=fnt, fill=(0, 0, 0))
    y += text_height + 10


# Show Preview
st.image(img, caption="Preview", use_column_width=True, channels="luminance")
