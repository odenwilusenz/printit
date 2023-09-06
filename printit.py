import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests, io, base64
import subprocess
import tempfile
import os
import re
import slugify
import random, string


# Function to find .ttf fonts
def find_fonts():
    font_dirs = ["fonts", "/usr/share/fonts/"]
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

def find_url(string):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    urls = re.findall(url_pattern, string)
    return urls

def img_concat_v(im1, im2):
    image_width=696
    dst = Image.new('RGB', (im1.width, im1.height + image_width))
    dst.paste(im1, (0, 0))
    im2 = im2.resize((image_width, image_width))

    dst.paste(im2, (0, im1.height))
    return dst






# Streamlit app
st.title('STICKER FACTORY @ TAMI')

st.subheader("hard copies of images, text and txt2img")
st.divider() 
st.subheader(":printer: a sticker")

uploaded_image = st.file_uploader("Choose an image file to :printer:", type=['png', 'jpg', 'gif'],)

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
    

    # print options
    colc, cold = st.columns(2)
    with colc:
        if st.button('Print Original Image'):
            print_image(original_image)
            st.success('Original image sent to printer!')
    with cold:
        if st.button('Print Dithered Image'):
            print_image(dithered_image)
            st.success('Dithered image sent to printer!')

    cole, colf = st.columns(2)
    with cole:
        if st.button('Print Original+rotated Image'):
            rotated_org_image = rotate_image(original_image, 90)
            print_image(rotated_org_image)
            st.success('Original+rotated image sent to printer!')

    with colf:
        if st.button('Print dithered+rotated Image'):
            rotated_image = rotate_image(dithered_image, 90)
            print_image(rotated_image)
            st.success('Dithered+rotated image sent to printer!')












st.divider() 
st.subheader(":printer: a label")

img = ""

# Function to calculate the actual image height based on the bounding boxes of each line
def calculate_actual_image_height_with_empty_lines(text, font, line_spacing=10):
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1), color="white"))  # Dummy image for calculation
    total_height = 0
    for line in text.split('\n'):
        if line.strip():  # Non-empty lines
            bbox = draw.textbbox((0, 0), line, font=font)
            text_height = bbox[3] - bbox[1]
        else:  # Empty lines
            text_height = font.getbbox("x")[3] - font.getbbox("x")[1]  # Use the height of 'x' as the height for empty lines
        total_height += text_height + line_spacing  # Add line spacing
    return total_height - line_spacing  # Remove the last line spacing

# Function to calculate the maximum font size based on the width of the longest line
def calculate_max_font_size(width, text, font_path, start_size=10, end_size=200, step=1):
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1), color="white"))  # Dummy image for calculation
    max_font_size = start_size

    for size in range(start_size, end_size, step):
        font = ImageFont.truetype(font_path, size)
        adjusted_lines = []
        for line in text.split('\n'):
            adjusted_lines.append(line)

        max_text_width = max([draw.textbbox((0, 0), line, font=font)[2] for line in adjusted_lines if line.strip()])
        
        if max_text_width <= width:
            max_font_size = size
        else:
            break

    return max_font_size


# Multiline Text Input
text = st.text_area("Enter your text","write something", height=200)
if text:                                                                                                                                                
    urls = find_url(text)
    if urls:
        st.success("Found URLs: we might automate the QR code TODO")                                                                                                                        
        for url in urls:
            st.write(url)  

    # init some font vars
    available_fonts = find_fonts()
    font=available_fonts[0]
    alignment = "center"
    fnt = ImageFont.truetype(font, 20) # Initialize Font
    max_size = calculate_max_font_size(696, text, font) 
    font_size = max_size
    
    fontstuff = st.checkbox("font settings", value=False)
    col1, col2 = st.columns(2)
    if fontstuff:
        # Font Selection
        with col1:
            font = st.selectbox("Choose your font", available_fonts)

        # Alignment
        with col2:
            alignment_options = ["left", "center", "right"]
            alignment = st.selectbox("Choose text alignment", alignment_options, index=1)
        font_size = st.slider("Font Size", 5, max_size+5, max_size)
        font_size
    # Font Size
    fnt = ImageFont.truetype(font, font_size) # Initialize Font
    line_spacing = 20  # Adjust this value to set the desired line spacing

    # Calculate the new image height based on the bounding boxes
    new_image_height = calculate_actual_image_height_with_empty_lines(text, fnt, line_spacing)

    # Create Image
    y = 5  # Start from
    img = Image.new("RGB", (696, new_image_height+10), color="white")
    d = ImageDraw.Draw(img)

    # Draw Text
    for line in text.split('\n'):
        text_width = 0  # Initialize to zero

        if line.strip():  # For non-empty lines
            bbox = d.textbbox((0, y), line, font=fnt)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:  # For empty lines
            text_height = fnt.getbbox("x ")[3] - fnt.getbbox("x")[1]  # Use the height of an x as the height for empty lines

        if alignment == "center":
            x = (696 - text_width) // 2
        elif alignment == "right":
            x = 696 - text_width
        else:
            x = 0

        d.text((x, y), line, font=fnt, fill=(0, 0, 0))
        y += text_height + line_spacing  # Move down based on text height and line spacing





# QR code


import qrcode
qr = qrcode.QRCode(
    border=0
)

qrurl = st.text_input("add a QRcode to your sticker",)
if qrurl:
    #we have text generate qr
    qr.add_data(qrurl)
    qr.make(fit=True)
    imgqr = qr.make_image(fill_color="black", back_color="white")

    #save to image
    # add random 4 letetrs to file name
    # letters = string.ascii_lowercase
    # random_string = ''.join(random.choice(letters) for i in range(4))
    # qrimgpath = os.path.join('temp', "qr_" + random_string + '.png')
    # imgqr.save(qrimgpath, "PNG")

    if imgqr and img:
        #add qr below the label
        imgqr = img_concat_v(img, imgqr)
        st.image(imgqr, use_column_width=True)
        if st.button('Print sticker+qr'):
                print_image(imgqr)
    elif imgqr and not(img):
        # st.image(imgqr, use_column_width=True)
        if st.button('Print sticker'):
                print_image(imgqr)


if text and not(qrurl):
    st.image(img, use_column_width=True)
    if st.button('Print sticker'):
            print_image(img)  # Needs definition
            st.success('sticker sent to printer')







st.divider() 
st.subheader(":printer: image from text")
st.write("using tami stable diffusion bot")
prompt = st.text_input("Enter a prompt")
if prompt:
    print("generating image from prompt: " + prompt)
    generatedImage = generate_image(prompt, 20)
    resized_image, dithered_image = resize_and_dither(generatedImage)
    st.image(resized_image, caption="Original Image")
    st.image(dithered_image, caption="Resized and Dithered Image")
    slugprompt = slugify.slugify(prompt)
    original_image_path = os.path.join('temp', "txt2img_" + slugprompt + '.png')
    #svae image
    generatedImage.save(original_image_path, "PNG")

    print_image(dithered_image)

st.subheader("FAQ:")
st.write("dithering is suggested if source is not lineart\ngrayscale and color look bad at thermal printer\nthats why we do dethering\nPRINT ALOT is the best!")
st.image(Image.open('assets/station_sm.jpg'), caption="TAMI printshop")
