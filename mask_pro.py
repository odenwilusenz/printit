import streamlit as st
from PIL import Image, ImageOps
import numpy as np
import cv2
import os
import usb.core
from brother_ql.conversion import convert
from brother_ql.backends import backend_factory
from brother_ql.raster import BrotherQLRaster
from brother_ql.models import ModelsManager
from brother_ql.backends.helpers import send
from datetime import datetime

def resize_image_to_width(image_path, output_path, target_width_mm, current_dpi):
    # Convert mm to inches (since DPI is dots per inch)
    target_width_inch = target_width_mm / 25.4

    # Open the image
    image = Image.open(image_path)

    # Calculate the target pixel width using the given DPI
    target_width_px = int(target_width_inch * current_dpi)

    # Calculate the aspect ratio to maintain the original height/width ratio
    aspect_ratio = image.height / image.width

    # Calculate the new height based on the target width and aspect ratio
    target_height_px = int(target_width_px * aspect_ratio)

    # Resize the image while maintaining the aspect ratio
    resized_image = image.resize((target_width_px, target_height_px), Image.LANCZOS)

    # If the resized width is less than 696 pixels, pad with white
    if target_width_px < 696:
        new_image = Image.new("RGB", (696, target_height_px), (255, 255, 255))
        new_image.paste(resized_image, ((696 - target_width_px) // 2, 0))
        resized_image = new_image

    # Save the resized image to the output path
    resized_image.save(output_path)
    print(f"Image resized to {resized_image.width}x{resized_image.height} pixels.")

def apply_threshold(image, threshold):
    return image.point(lambda x: 255 if x > threshold else 0, mode='1')

def apply_canny(image, threshold1, threshold2):
    image_np = np.array(image)
    edges = cv2.Canny(image_np, threshold1, threshold2)
    edges_inverted = cv2.bitwise_not(edges)
    return Image.fromarray(edges_inverted)

def mirror_image(image):
    return ImageOps.mirror(image)

def find_and_parse_printer():
    model_manager = ModelsManager()

    for backend_name in ['pyusb', 'linux_kernel']:
        backend = backend_factory(backend_name)
        for printer in backend['list_available_devices']():
            identifier = printer['identifier']
            parts = identifier.split('/')

            if len(parts) < 4:
                continue

            protocol = parts[0]
            device_info = parts[2]
            serial_number = parts[3]
            vendor_id, product_id = device_info.split(':')

            model = 'QL-570'
            for m in model_manager.iter_elements():
                if m.product_id == int(product_id, 16):
                    model = m.identifier
                    break

            return {
                'identifier': identifier,
                'backend': backend_name,
                'model': model,
                'protocol': protocol,
                'vendor_id': vendor_id,
                'product_id': product_id,
                'serial_number': serial_number
            }

    return None

def print_label(printer_info, image_path, label_size, dpi, dither=False, rotate=0):
    qlr = BrotherQLRaster(printer_info['model'])
    instructions = convert(
        qlr=qlr,
        images=[image_path],
        label=label_size,
        rotate=rotate,
        threshold=0,
        dither=dither,
        compress=False,
        red=False,
        dpi_600=False,
        hq=True,
        cut=True
    )

    try:
        return send(instructions=instructions, printer_identifier=printer_info['identifier'], backend_identifier='pyusb')
    except usb.core.USBError as e:
        if "timeout error" in str(e):
            print("USB timeout error occurred, but it's okay.")
            return True
        print(f"USBError encountered: {e}")
        return False

def apply_dithering(image):
    # Ensure the image is in grayscale mode
    if image.mode != 'L':
        image = image.convert('L')
    # Apply Floyd-Steinberg dithering
    dithered_image = image.convert('1', dither=Image.FLOYDSTEINBERG)
    return dithered_image

def main():
    st.title("mask print ++")

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        # Create a temporary folder within the script folder
        temp_folder = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_folder, exist_ok=True)

        # Get the current date and format it
        current_date = datetime.now().strftime("%Y%m%d")

        # Get the uploaded filename and prepend the date
        uploaded_filename = uploaded_file.name
        new_filename = f"{current_date}_{uploaded_filename}"

        # Save the original image to the temporary folder with the new filename
        original_image_path = os.path.join(temp_folder, new_filename)

        image = Image.open(uploaded_file)
        image.save(original_image_path)
        image = image.convert('L')

        # Resize the image to a smaller dimension of 696 pixels while maintaining aspect ratio
        width, height = image.size
        target_size = 696 * 2
        if min(width, height) != target_size:
            if width < height:
                new_width = target_size
                new_height = int((target_size / width) * height)
            else:
                new_height = target_size
                new_width = int((target_size / height) * width)
            image = image.resize((new_width, new_height))

        col1, col2 = st.columns([1, 1])

        with col1:
            image_path = "latest.png"
            print_choice = st.radio("Choose which image to print/save:", ("Original", "Threshold"))

            st.text("General options:")
            mirror_checkbox = st.checkbox("Mirror Mask", value=False)

            target_width_mm = st.number_input("Target Width (mm)", min_value=0, value=0)

            rotate_disabled = target_width_mm > 0
            rotate_checkbox = st.checkbox("rotate 90deg", value=False, disabled=rotate_disabled)
            rotate = 90 if rotate_checkbox else 0

            # Define current_dpi with a default value
            current_dpi = 300

            if target_width_mm > 0:
                current_dpi = 300  # st.number_input("Current DPI", min_value=1, value=300)
                resized_image_path = os.path.join(temp_folder, f"resized_{new_filename}")
                resize_image_to_width(original_image_path, resized_image_path, target_width_mm, current_dpi)
                image = Image.open(resized_image_path)

            if mirror_checkbox:
                image = mirror_image(image)

            dither = True
            if print_choice == "Original":
                dither = st.checkbox("Dither - approximate grey tones with dithering", value=True)
                image.save(image_path)

            elif print_choice == "Threshold":
                threshold_percent = st.slider("Threshold (%)", 0, 100, 50)
                threshold = int(threshold_percent * 255 / 100)
                threshold_image = apply_threshold(image, threshold)
                threshold_image.save(image_path)

        with col2:
            st.image(image_path, caption="", use_column_width=True)

        print_button_label = f"Print {print_choice} Image"
        if print_choice == "Original" and dither:
            print_button_label += ", Dithering"
        if rotate_checkbox:
            print_button_label += ", Rotated 90°"
        if mirror_checkbox:
            print_button_label += ", Mirrored"

        if st.button(print_button_label):
            printer_info = find_and_parse_printer()
            if not printer_info:
                st.error("No Brother QL printer found. Please check the connection and try again.")
            else:
                label_size = '62'
                if print_label(printer_info, image_path, label_size, dpi=current_dpi, dither=dither, rotate=rotate):
                    st.success("mask printed")
                else:
                    st.error("Printing failed.")

if __name__ == "__main__":
    main()