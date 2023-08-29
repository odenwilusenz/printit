import streamlit as st
from PIL import Image
import numpy as np
import cv2
import subprocess
import tempfile
import os

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
st.title('STICKER FACTORY in TAMI')
st.subheader("dithering is suggested if source is not lineart\n\nPRINT ALOT is the best!")
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
