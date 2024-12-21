import streamlit as st
from PIL import Image, ImageOps
import os
import usb.core
from brother_ql.conversion import convert
from brother_ql.backends import backend_factory
from brother_ql.raster import BrotherQLRaster
from brother_ql.models import ModelsManager
from brother_ql.backends.helpers import send
from brother_ql import labels  # Import the labels module
from datetime import datetime
import tempfile
import subprocess

def find_and_parse_printer():
    model_manager = ModelsManager()

    for backend_name in ["pyusb", "linux_kernel"]:
        backend = backend_factory(backend_name)
        for printer in backend["list_available_devices"]():
            identifier = printer["identifier"]
            parts = identifier.split("/")

            if len(parts) < 4:
                continue

            protocol = parts[0]
            device_info = parts[2]
            serial_number = parts[3]
            vendor_id, product_id = device_info.split(":")

            model = "QL-570"  # default model
            for m in model_manager.iter_elements():
                if m.product_id == int(product_id, 16):
                    model = m.identifier
                    break

            return {
                "identifier": identifier,
                "backend": backend_name,
                "model": model,
                "protocol": protocol,
                "vendor_id": vendor_id,
                "product_id": product_id,
                "serial_number": serial_number,
            }       
        return None

def get_printer_label_info():
    printer_info = find_and_parse_printer()
    if not printer_info:
        return None, "No printer found"
    
    try:
        # Use brother_ql command line tool to get status
        cmd = f"brother_ql -b pyusb --model {printer_info['model']} -p {printer_info['identifier']} status"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return None, "Could not get printer status"
        
        status_output = result.stdout
        print(f"Printer status output: {status_output}")  # Debug print
        
        # Parse the status output
        media_width_mm = None
        
        for line in status_output.split('\n'):
            if 'Media size:' in line:
                try:
                    # Extract just the number before 'x'
                    width_str = line.split(':')[1].split('x')[0].strip()
                    media_width_mm = int(width_str)
                    print(f"Detected media width: {media_width_mm}mm")  # Debug print
                except ValueError:
                    continue
        
        # Map physical width in mm to brother_ql label types
        label_sizes = {
            12: "12",     # 106 dots printable
            29: "29",     # 306 dots printable
            38: "38",     # 413 dots printable
            50: "50",     # 554 dots printable
            54: "54",     # 590 dots printable
            62: "62",     # 696 dots printable
            102: "102",   # 1164 dots printable
            103: "103",   # 1200 dots printable
            104: "104"    # 1200 dots printable
        }
        
        if media_width_mm in label_sizes:
            label_type = label_sizes[media_width_mm]
            return label_type, f"Detected {label_type} ({media_width_mm}mm)"
        
        return None, f"Unknown label width: {media_width_mm}mm"
        
    except Exception as e:
        return None, f"Error getting printer status: {str(e)}"

def get_label_type():
    """
    Determine label type in order of precedence:
    1. From printer's current media (most accurate)
    2. From secrets.toml configuration (fallback)
    3. Default to "62" with warning
    """
    # Try to detect from printer's current media
    detected_label, status_message = get_printer_label_info()
    if detected_label:
        return detected_label, status_message

    # Try to get from secrets.toml
    if "label_type" in st.secrets:
        return st.secrets["label_type"], "Using configured label_type from secrets"

    # If neither works, return default with warning
    st.warning("⚠️ No label type detected from printer and none configured in secrets.toml. Using default label type 62")
    return "62", "Using default label type 62"

def get_label_width(label_type):
    label_definitions = labels.ALL_LABELS
    for label in label_definitions:
        if label.identifier == label_type:
            width = label.dots_printable[0]
            print(f"Label type {label_type} width: {width} dots")  # Debug print
            return width
    raise ValueError(f"Label type {label_type} not found in label definitions")

# Get label type and status message at startup
label_type, label_status = get_label_type()
label_width = get_label_width(label_type)

def apply_threshold(image, threshold):
    # Ensure the image is in grayscale mode
    if image.mode != 'L':
        image = image.convert('L')

    # Create a LUT with 256 entries
    lut = [255 if i > threshold else 0 for i in range(256)]
    return image.point(lut, mode='1')

def mirror_image(image):
    return ImageOps.mirror(image)

def preper_image(image, label_width=label_width):
    # Debug print original image size
    print(f"Original image size: {image.size}")
    
    if image.mode == "RGBA":
        white_background = Image.new("RGBA", image.size, "white")
        white_background.paste(image, mask=image.split()[3])
        image = white_background

    # Only resize if the image width doesn't match label width
    width, height = image.size
    if width != label_width:
        # Calculate new height maintaining aspect ratio
        new_height = int((label_width / width) * height)
        image = image.resize((label_width, new_height))
        print(f"Resizing image from ({width}, {height}) >> {image.size}")

    # Convert to grayscale if needed
    if image.mode != "L":
        grayscale_image = image.convert("L")
    else:
        grayscale_image = image

    # Apply Floyd-Steinberg dithering
    dithered_image = grayscale_image.convert("1", dither=Image.FLOYDSTEINBERG)

    return grayscale_image, dithered_image

def print_image(image, rotate=0, dither=False):
    # Ensure the temporary directory exists
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)

    # Save the image to a temporary file
    with tempfile.NamedTemporaryFile(
        suffix=".png", delete=False, dir=temp_dir
    ) as temp_file:
        temp_file_path = temp_file.name
        image.save(temp_file_path, "PNG")
        print(f"Image saved to: {temp_file_path}")  # Print the full path

    # Use find_and_parse_printer to get printer information
    printer_info = find_and_parse_printer()
    if not printer_info:
        st.error(
            "No Brother QL printer found. Please check the connection and try again."
        )
        return False

    # Construct the print command for logging
    command = f"brother_ql -b {printer_info['backend']} --model {printer_info['model']} -p {printer_info['identifier']} print -l {label_type} \"{temp_file_path}\""
    print(f"Equivalent CLI command: \n{command}")  # Log the command to standard output

    # Prepare the image for printing
    qlr = BrotherQLRaster(printer_info["model"])
    instructions = convert(
        qlr=qlr,
        images=[temp_file_path],
        label=label_type,
        rotate=rotate,
        threshold=70,  # Default CLI threshold
        dither=dither,
        compress=True,  # CLI uses compression by default
        red=False,
        dpi_600=False,
        hq=False,  # CLI doesn't use HQ by default
        cut=True,
    )

    # Debug logging
    print(f"""
    Print parameters:
    - Label type: {label_type}
    - Rotate: {rotate}
    - Dither: {dither}
    - Model: {printer_info['model']}
    - Backend: {printer_info['backend']}
    - Identifier: {printer_info['identifier']}
    """)

    # Try to print using Python API
    try:
        success = send(
            instructions=instructions,
            printer_identifier=printer_info["identifier"],
            backend_identifier="pyusb",
        )
        
        if not success:
            st.error("Failed to print using Python API")
            return False
            
    except usb.core.USBError as e:
        if "timeout error" in str(e):
            print("USB timeout error occurred, but it's okay.")
            return True
        print(f"USBError encountered: {e}")
        st.error(f"USBError encountered: {e}")
        return False

    return True

def resize_image_to_width(image, target_width_mm, current_dpi=300):
    # Convert mm to inches (since DPI is dots per inch)
    target_width_inch = target_width_mm / 25.4

    # Calculate the target pixel width using the given DPI
    target_width_px = int(target_width_inch * current_dpi)

    # Get current dimensions
    current_width = image.width

    # Calculate scaling factor based on target width
    scale_factor = target_width_px / current_width

    # Calculate new height maintaining aspect ratio
    new_height = int(image.height * scale_factor)

    # Resize the image while maintaining the aspect ratio
    resized_image = image.resize((target_width_px, new_height), Image.LANCZOS)

    # If the resized width is less than label_width pixels, pad with white
    if target_width_px < label_width:
        new_image = Image.new("RGB", (label_width, new_height), (255, 255, 255))
        new_image.paste(resized_image, ((label_width - target_width_px) // 2, 0))
        resized_image = new_image

    print(f"Image resized from {image.width}x{image.height} to {resized_image.width}x{resized_image.height} pixels.")
    print(f"Target width was {target_width_mm}mm ({target_width_px}px)")
    return resized_image

def add_border(image, border_width=1):
    """Add a thin black border around the image"""
    if image.mode == '1':  # Binary image
        # For binary images, create a new binary image with border
        bordered = Image.new('1', (image.width + 2*border_width, image.height + 2*border_width), 0)  # 0 is black
        bordered.paste(image, (border_width, border_width))
        return bordered
    else:
        # For other modes, use ImageOps
        return ImageOps.expand(image, border=border_width, fill='black')

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

        col1, col2 = st.columns([1, 1])

        with col1:
            print_choice = st.radio("Choose which image to print/save:", ("Original", "Threshold"))

            st.text("General options:")
            mirror_checkbox = st.checkbox("Mirror Mask", value=False)
            border_checkbox = st.checkbox("Show border in preview", value=True, help="Adds a border in the preview to help visualize boundaries (not printed)")
            
            # Add target width in mm option
            target_width_mm = st.number_input("Target Width (mm)", min_value=0, value=0)
            
            # Disable rotation if target width is specified
            rotate_disabled = target_width_mm > 0
            rotate_checkbox = st.checkbox("rotate 90deg", value=False, disabled=rotate_disabled)
            if rotate_disabled and rotate_checkbox:
                st.info("Rotation disabled when target width is specified")
            
            # Apply target width resizing if specified
            if target_width_mm > 0:
                image = resize_image_to_width(image, target_width_mm)
            
            if mirror_checkbox:
                image = mirror_image(image)

            # Process image based on choice
            if print_choice == "Original":
                dither = st.checkbox("Dither - approximate grey tones with dithering", value=True)
                grayscale_image, dithered_image = preper_image(image)
                display_image = dithered_image if dither else grayscale_image
            else:  # Threshold
                threshold_percent = st.slider("Threshold (%)", 0, 100, 50)
                threshold = int(threshold_percent * 255 / 100)
                display_image = apply_threshold(image, threshold)

            # Create a copy for display with border if needed
            preview_image = display_image.copy()
            if border_checkbox:
                preview_image = add_border(preview_image)

        with col2:
            st.image(preview_image, caption="Preview", use_column_width=True)

        print_button_label = f"Print {print_choice} Image"
        if print_choice == "Original" and dither:
            print_button_label += ", Dithering"
        if rotate_checkbox and not rotate_disabled:
            print_button_label += ", Rotated 90°"
        if mirror_checkbox:
            print_button_label += ", Mirrored"
        if target_width_mm > 0:
            print_button_label += f", Width: {target_width_mm}mm"

        if st.button(print_button_label):
            rotate = 90 if (rotate_checkbox and not rotate_disabled) else 0
            if print_choice == "Original":
                success = print_image(grayscale_image, rotate=rotate, dither=dither)
            else:
                success = print_image(display_image, rotate=rotate, dither=False)
                
            if success:
                st.success("Image printed successfully!")
            else:
                st.error("Printing failed. Please check the printer connection.")

if __name__ == "__main__":
    main()
