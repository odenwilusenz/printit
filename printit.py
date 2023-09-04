import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests, io, base64
import subprocess
import tempfile
import os
import slugify

# Function to find .ttf fonts
def find_fonts():
    font_dirs = ["/usr/share/fonts/truetype", "fonts"]
    fonts = []
    for dir in font_dirs:
        if os.path.exists(dir):
            for root, _, files in os.walk(dir):
                for file in files:
                    if file.endswith(".ttf"):
                        fonts.append(os.path.join(root, file))
    return fonts

def generate_image(prompt, steps):
    payload = {
        "prompt": prompt,
        "steps": 16,
        "width": 696
    }
    
    response = requests.post(url=f'https://y7bbzpsxx1vt.share.zrok.io/sdapi/v1/txt2img', json=payload)
    r = response.json()
    
    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
        return image
    
def add_white_background_and_convert_to_grayscale(image):
    # Check if the image has transparency (an alpha channel)
    if image.mode == 'RGBA':
        # Create a white background of the same size as the original image
        white_background = Image.new('RGBA', image.size, 'white')
        # Paste the original image onto the white background
        white_background.paste(image, mask=image.split()[3]) # Using the alpha channel as the mask
        image = white_background

    # Convert the image to grayscale
    return image.convert('L')

def rotate_image(image, angle):
    return image.rotate(angle, expand=True)

def resize_and_dither(image):
    # Resize the image to 696 width while maintaining the aspect ratio
    new_width = 696
    aspect_ratio = image.width / image.height
    new_height = int(new_width / aspect_ratio)
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    # Convert the resized image to grayscale
    resized_grayscale_image = resized_image.convert("L")

    # Apply Floyd-Steinberg dithering
    dithered_image = resized_grayscale_image.convert("1", dither=Image.FLOYDSTEINBERG)
    
    return resized_grayscale_image, dithered_image


def print_image(image):
    # Save the image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_file_path = temp_file.name
        image.save(temp_file_path, "PNG")
        
    # Construct the print command
    command = f"brother_ql -b pyusb --model QL-570 -p usb://0x04f9:0x2028/000M6Z401370 print -l 62 \"{temp_file_path}\""
    
    # Run the print command
    subprocess.run(command, shell=True)

# Streamlit app
st.title('STICKER FACTORY @ TAMI')

st.subheader("Choose an image file (png/jpg/gif)")
uploaded_image = st.file_uploader("Choose an image file (png/jpg/gif)", type=['png', 'jpg', 'gif'])

if uploaded_image is not None:
    original_image = Image.open(uploaded_image).convert('RGB')
    # Get the original filename without extension
    original_filename_without_extension = os.path.splitext(uploaded_image.name)[0]
    grayimage = add_white_background_and_convert_to_grayscale(original_image)
    resized_image, dithered_image = resize_and_dither(grayimage)
    
    st.image(original_image, caption="Original Image")
    st.image(dithered_image, caption="Resized and Dithered Image")


    # Paths to save the original and dithered images in the 'temp' directory with postfix
    original_image_path = os.path.join('temp', original_filename_without_extension + '_original.png')
    dithered_image_path = os.path.join('temp', original_filename_without_extension + '_dithered.png')

    # Save both original and dithered images
    original_image.save(original_image_path, "PNG")
    dithered_image.save(dithered_image_path, "PNG")
    
    rotated_image = rotate_image(dithered_image, 90)
    rotated_org_image = rotate_image(original_image, 90)

    print(dithered_image_path)
    # Print options
    if st.button('Print Original Image'):
        print_image(original_image)
        st.success('Original image sent to printer!')
    if st.button('Print Original+rotated Image'):
        print_image(original_image)
        st.success('Original+rotated image sent to printer!')

    if st.button('Print Dithered Image'):
        print_image(dithered_image)
        st.success('Dithered image sent to printer!')

    if st.button('Print dithered+rotated Image'):
        print_image(rotated_image)
        st.success('Dithered+rotated image sent to printer!')

st.subheader("or print some text")

# Multiline Text Input
text = st.text_area("Enter your text", "write")

col1, col2 = st.columns(2)

# Font Selection
with col1:
    available_fonts = find_fonts()
    font = st.selectbox("Choose your font", available_fonts)

# Alignment
with col2:
    alignment_options = ["left", "center", "right"]
    alignment = st.selectbox("Choose text alignment", alignment_options, index=1)


# Font Size
font_size = st.slider("Font Size", 10, 200, 50)

# Calculate Image Height
num_lines = len(text.split('\n'))-1
image_height = num_lines * (font_size + 10)  # 10 is line spacing

# Create Image
img = Image.new("RGB", (696, image_height), color="white")
d = ImageDraw.Draw(img)
fnt = ImageFont.truetype(font, font_size)

# Draw Text
y = 5
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
st.image(img, use_column_width=True, channels="luminance")
if st.button('Print label'):
    print_image(img)
    st.success('label sent to printer!')

st.subheader("or generate an image from text")
prompt = st.text_input("Enter a prompt")
if prompt:
    generatedImage = generate_image(prompt, 20)
    resized_image, dithered_image = resize_and_dither(generatedImage)
    st.image(resized_image, caption="Original Image")
    st.image(dithered_image, caption="Resized and Dithered Image")
    slugprompt = slugify.slugify(prompt)
    original_image_path = os.path.join('temp', "txt2img_" + slugprompt + '.png')

    print_image(dithered_image)

st.subheader("FAQ:")
st.write("dithering is suggested if source is not lineart\ngrayscale and color look bad at thermal printer\nthats why we do dethering\nPRINT ALOT is the best!")
st.image(Image.open('temp/PXL_20230829_213310190_original.png'), caption="TAMI printshop")