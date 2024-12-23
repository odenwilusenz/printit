import streamlit as st
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
import requests
import io
import glob
import base64
import os
import re
import tempfile
from datetime import datetime
import time
import qrcode
from brother_ql.models import ModelsManager
from brother_ql.backends import backend_factory
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql import labels  # Import the labels module
import usb.core
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

# Get label type and status message
label_type, label_status = get_label_type()

if 'txt2img_url' not in st.secrets:
    st.warning("⚠️ txt2img_url not found in secrets. Using default localhost:8670")
    txt2img_url = "http://localhost:8670"
else:
    txt2img_url = st.secrets['txt2img_url']


def get_label_width(label_type):
    label_definitions = labels.ALL_LABELS
    for label in label_definitions:
        if label.identifier == label_type:
            width = label.dots_printable[0]
            print(f"Label type {label_type} width: {width} dots")  # Debug print
            return width
    raise ValueError(f"Label type {label_type} not found in label definitions")


label_width = get_label_width(label_type)  # Use the width as label_width


# Check if the 'copy' parameter exists
# add to url "?copy=25"
copy = int(st.query_params.get("copy", [1])[0])  # Default to 1 copy if not specified


# Function to list saved images with optional duplicate filtering
def list_saved_images(filter_duplicates=True):
    # Get history limit from secrets with default fallback of 15
    history_limit = st.secrets.get("history_limit", 15)
    
    # Get all image files from both temp and labels folders
    temp_files = glob.glob(os.path.join("temp", "*.[pj][np][g]*"))
    label_files = glob.glob(os.path.join("labels", "*.[pj][np][g]*"))

    # Combine all image files
    image_files = temp_files + label_files

    # Filter out test labels and get valid images
    valid_images = [
        f for f in image_files 
        if "write_something" not in os.path.basename(f).lower()
    ]

    if not filter_duplicates:
        # Simply return all files sorted by modification time
        return sorted(valid_images, key=os.path.getmtime, reverse=True)[:history_limit]

    # Create a dictionary to store the latest version of each unique image size
    unique_images = {}

    for image_path in valid_images:
        try:
            # Get file size in bytes
            file_size = os.path.getsize(image_path)
            
            # If this size already exists, compare modification times
            if file_size in unique_images:
                existing_time = os.path.getmtime(unique_images[file_size])
                current_time = os.path.getmtime(image_path)
                if current_time > existing_time:
                    unique_images[file_size] = image_path
            else:
                unique_images[file_size] = image_path
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            continue

    # Sort by modification time (newest first)
    return sorted(unique_images.values(), key=os.path.getmtime, reverse=True)[:history_limit]


# Function to find .ttf fonts
def find_fonts():
    font_dirs = [
        "fonts",  # Local fonts directory
        "/usr/share/fonts/",  # Linux system fonts
        "C:/Windows/Fonts/",  # Windows system fonts
        os.path.expanduser("~/.fonts/"),  # Linux user fonts
        os.path.expanduser("~/Library/Fonts/"),  # macOS user fonts
        "/Library/Fonts/",  # macOS system fonts
    ]

    fonts = []
    for dir in font_dirs:
        if os.path.exists(dir):
            # Walk through directory and subdirectories
            for root, _, files in os.walk(dir):
                for file in files:
                    if file.lower().endswith((".ttf", ".otf")):  # Added .otf support
                        try:
                            font_path = os.path.join(root, file)
                            # Verify it's a valid font by attempting to load it
                            ImageFont.truetype(font_path, 12)
                            fonts.append(font_path)
                        except Exception:
                            # Skip invalid fonts
                            continue

    # Remove duplicates while preserving order
    return list(dict.fromkeys(fonts))


def safe_filename(text):
    # Sanitize the text to remove illegal characters and replace spaces with underscores
    sanitized_text = re.sub(r'[<>:"/\\|?*\n\r]+', "", text).replace(" ", "_")
    # Get the current time in epoch format
    epoch_time = int(time.time())
    # Return the filename
    return f"{epoch_time}_{sanitized_text}.png"


# Ensure label directory exists
label_dir = "labels"
os.makedirs(label_dir, exist_ok=True)


def generate_image(prompt, steps):
    payload = {"prompt": prompt, "steps": steps, "width": label_width}
    
    # Get txt2img_url from secrets with default fallback
    txt2img_url = st.secrets.get("txt2img_url", "http://localhost:7860")
    
    # Show warning if using default URL
    if txt2img_url == "http://localhost:7860":
        st.warning("Using default Stable Diffusion URL (http://localhost:7860). Configure txt2img_url in .streamlit/secrets.toml for custom endpoint.")

    try:
        response = requests.post(url=f'{txt2img_url}/sdapi/v1/txt2img', json=payload)

        # Check if the request was successful
        response.raise_for_status()

        # Print raw response content for debugging
        print("Raw response content:", response.content)

        r = response.json()

        if r["images"]:
            first_image = r["images"][0]
            base64_data = (
                first_image.split("base64,")[1]
                if "base64," in first_image
                else first_image
            )
            image = Image.open(io.BytesIO(base64.b64decode(base64_data)))

            png_payload = {"image": "data:image/png;base64," + first_image}
            response2 = requests.post(
                url=f"{txt2img_url}/sdapi/v1/png-info", json=png_payload
            )
            response2.raise_for_status()

            # save image
            pnginfo = PngImagePlugin.PngInfo()
            info = response2.json().get("info")
            if info:
                pnginfo.add_text("parameters", str(info))
            current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            filename = os.path.join(temp_dir, "txt2img_" + current_date + ".png")
            image.save(filename, pnginfo=pnginfo)

            return image
        else:
            print("No images found in the response")
            return None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
        return None
    except ValueError as e:
        print(f"An error occurred while parsing the JSON response: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def preper_image(image, label_width=label_width):
    # Debug print original image size
    # print(f"Original image size: {image.size}")
    
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
        return

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


def find_url(string):
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )
    urls = re.findall(url_pattern, string)
    return urls


def img_concat_v(im1, im2, image_width=label_width):
    dst = Image.new("RGB", (im1.width, im1.height + image_width))
    dst.paste(im1, (0, 0))
    im2 = im2.resize((image_width, image_width))

    dst.paste(im2, (0, im1.height))
    return dst


def get_cat_breeds():
    cat_api_key = st.secrets.get("cat_api_key", "")
    if not cat_api_key or cat_api_key == "ask me":
        return ["API key required"]
    
    try:
        response = requests.get(
            "https://api.thecatapi.com/v1/breeds",
            headers={"x-api-key": cat_api_key}
        )
        breeds = response.json()
        return [breed["name"] for breed in breeds]
    except:
        return ["Error fetching breeds"]


# Streamlit app
if not os.path.exists(".streamlit/secrets.toml"):
    st.error("⚠️ No secrets.toml file found!")
    st.info("""
    Please set up your `.streamlit/secrets.toml` file:
    1. Copy the example file: `cp .streamlit/secrets.toml.example .streamlit/secrets.toml`
    2. Edit the file with your settings
    
    The app will try to auto-detect your printer's label type, but you can override it in secrets.toml if needed.
    See the example file for all available options and their descriptions.
    """)

st.title(st.secrets.get("title", "STICKER FACTORY"))

st.subheader(":printer: hard copies of images and text")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["Sticker", "Label", "Text2image", "Webcam", "Cat", "history", "FAQ"]
)

# Initialize the session state for the prompt and image
if "prompt" not in st.session_state:
    st.session_state.prompt = ""
if "generated_image" not in st.session_state:
    st.session_state.generated_image = None


def submit():
    st.session_state.prompt = st.session_state.widget
    st.session_state.widget = ""
    st.session_state.generated_image = (
        None  # Reset the generated image when a new prompt is entered
    )

# sticker
with tab1:
    st.subheader("Sticker")

    # Allow the user to upload an image
    uploaded_image = st.file_uploader(
        "Choose an image file to print", type=["png", "jpg", "gif", "webp"]
    )

    # Initialize a variable for the image to be processed
    image_to_process = None
    filename = None  # To hold the filename without extension

    # Check if an image has been uploaded
    if uploaded_image is not None:
        # Convert the uploaded file to a PIL Image
        image_to_process = Image.open(uploaded_image).convert("RGB")
        filename = os.path.splitext(uploaded_image.name)[0]

        # Get the original filename without extension
        original_filename_without_extension = (
            os.path.splitext(uploaded_image.name)[0]
            if uploaded_image
            else "selected_image"
        )

        # grayimage = add_white_background_and_convert_to_grayscale(image_to_process)
        grayscale_image, dithered_image = preper_image(image_to_process)

        # Paths to save the original and dithered images in the 'temp' directory with postfix
        original_image_path = os.path.join(
            "temp", original_filename_without_extension + "_original.png"
        )

        # Create checkboxes for rotation and dithering (dither default to True) inline
        col1, col2 = st.columns(2)
        with col1:
            dither_checkbox = st.checkbox(
                "Dither - _use for high detail, true by default_", value=True
            )
        with col2:
            rotate_checkbox = st.checkbox("Rotate - _90 degrees_")

        # Determine the button text based on checkbox states
        button_text = "Print "
        if rotate_checkbox:
            button_text += "Rotated "
        if dither_checkbox:
            button_text += "Dithered "
        button_text += "Image"

        # Create a single button with dynamic text
        if st.button(button_text):
            rotate_value = 90 if rotate_checkbox else 0
            dither_value = dither_checkbox
            print_image(image_to_process, rotate=rotate_value, dither=dither_value)

        # Display image based on checkbox status
        if dither_checkbox:
            st.image(dithered_image, caption="Resized and Dithered Image")
        else:
            st.image(image_to_process, caption="Original Image")

        # Create 'temp' directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save original image
        image_to_process.save(original_image_path, "PNG")

# label
with tab2:
    st.subheader(":printer: a label")

    img = ""

    # Function to calculate the actual image height based on the bounding boxes of each line
    def calculate_actual_image_height_with_empty_lines(text, font, line_spacing=10):
        draw = ImageDraw.Draw(
            Image.new("RGB", (1, 1), color="white")
        )  # Dummy image for calculation
        total_height = 0

        # Get font metrics for consistent spacing
        ascent, descent = font.getmetrics()
        font_height = ascent + descent

        for line in text.split("\n"):
            if line.strip():  # Non-empty lines
                # Use textbbox for more accurate measurements
                bbox = draw.textbbox((0, 0), line, font=font)
                text_height = max(
                    bbox[3] - bbox[1], font_height
                )  # Use the larger of bbox height or font height
            else:  # Empty lines
                text_height = font_height

            total_height += text_height + line_spacing

        # Add padding at top and bottom
        padding = 20
        return total_height + (padding * 2)  # Add padding to total height

    # Function to calculate the maximum font size based on the width of the longest line
    def calculate_max_font_size(
        width, text, font_path, start_size=10, end_size=200, step=1
    ):
        draw = ImageDraw.Draw(
            Image.new("RGB", (1, 1), color="white")
        )  # Dummy image for calculation
        max_font_size = start_size

        for size in range(start_size, end_size, step):
            font = ImageFont.truetype(font_path, size)
            adjusted_lines = []
            for line in text.split("\n"):
                adjusted_lines.append(line)

            max_text_width = max(
                [
                    draw.textbbox((0, 0), line, font=font)[2]
                    for line in adjusted_lines
                    if line.strip()
                ]
            )

            if max_text_width <= width:
                max_font_size = size
            else:
                break

        return max_font_size

    # Multiline Text Input
    text = st.text_area("Enter your text to print", "write something", height=200)
    # Check if the text has been changed by the user
    if text:
        urls = find_url(text)
        if urls:
            st.success("Found URLs: we might automate the QR code TODO")
            for url in urls:
                st.write(url)

        # init some font vars
        available_fonts = find_fonts()
        font = available_fonts[0]
        alignment = "center"
        fnt = ImageFont.truetype(font, 20)  # Initialize Font
        max_size = calculate_max_font_size(label_width, text, font)
        font_size = max_size

        # Initialize font selection in session state if not already present
        if "selected_font" not in st.session_state:
            st.session_state.selected_font = available_fonts[0]

        fontstuff = st.checkbox("font settings", value=False)
        col1, col2 = st.columns(2)
        if fontstuff:
            # Font Selection with session state
            with col1:
                font = st.selectbox(
                    "Choose your font",
                    available_fonts,
                    index=available_fonts.index(st.session_state.selected_font),
                )
                st.session_state.selected_font = font

            # Alignment
            with col2:
                alignment_options = ["left", "center", "right"]
                alignment = st.selectbox(
                    "Choose text alignment", alignment_options, index=1
                )
            font_size = st.slider("Font Size", 5, max_size + 5, max_size)
            font_size
        # Font Size
        fnt = ImageFont.truetype(font, font_size)  # Initialize Font
        line_spacing = 20  # Adjust this value to set the desired line spacing

        # Calculate the new image height based on the bounding boxes
        new_image_height = calculate_actual_image_height_with_empty_lines(
            text, fnt, line_spacing
        )

        # Create Image with padding
        padding = 20  # Consistent with the padding in calculate_actual_image_height
        img = Image.new("RGB", (label_width, new_image_height), color="white")
        d = ImageDraw.Draw(img)

        # Adjust starting y position to account for padding
        y = padding  # Start from padding instead of 5

        # Draw Text
        for line in text.split("\n"):
            text_width = 0
            ascent, descent = fnt.getmetrics()
            font_height = ascent + descent

            if line.strip():  # For non-empty lines
                bbox = d.textbbox((0, y), line, font=fnt)
                text_width = bbox[2] - bbox[0]
                text_height = max(bbox[3] - bbox[1], font_height)
            else:  # For empty lines
                text_height = font_height

            if alignment == "center":
                x = (label_width - text_width) // 2
            elif alignment == "right":
                x = label_width - text_width
            else:
                x = 0

            d.text((x, y), line, font=fnt, fill=(0, 0, 0))
            y += text_height + line_spacing

        # Save the label image
        if text != "write something":
            filename = safe_filename(text)
            file_path = os.path.join(label_dir, filename)
            img.save(file_path, "PNG")
            st.success(f"Label saved as {filename}")

    # QR code
    qr = qrcode.QRCode(border=0)

    qrurl = st.text_input(
        "add a QRcode to your sticker",
    )
    if qrurl:
        # we have text generate qr
        qr.add_data(qrurl)
        qr.make(fit=True)
        imgqr = qr.make_image(fill_color="black", back_color="white")

        # save to image
        # add random 4 letetrs to file name
        # letters = string.ascii_lowercase
        # random_string = ''.join(random.choice(letters) for i in range(4))
        # qrimgpath = os.path.join('temp', "qr_" + random_string + '.png')
        # imgqr.save(qrimgpath, "PNG")

        if imgqr and img:
            # add qr below the label
            imgqr = img_concat_v(img, imgqr)
            st.image(imgqr, use_column_width=True)
            if st.button("Print sticker+qr"):
                print_image(imgqr)
        elif imgqr and not (img):
            # st.image(imgqr, use_column_width=True)
            if st.button("Print sticker"):
                print_image(imgqr)

    if text and not (qrurl):
        st.image(img, use_column_width=True)
        if st.button("Print sticker"):
            print_image(img)  # Needs definition
            st.success("sticker sent to printer")
    st.markdown(
        """
                * label will automaticly resize to fit the longest line, so use linebreaks.
                * on pc `ctrl+enter` will submit, on mobile click outside the `text_area` to process.
                """
    )

# text2img
with tab3:
    st.subheader(":printer: image from text")
    st.write("using tami stable diffusion bot")

    st.text_input("Enter a prompt", key="widget", on_change=submit)
    prompt = st.session_state.prompt

    if prompt and st.session_state.generated_image is None:
        st.write("Generating image from prompt: " + prompt)
        generated_image = generate_image(prompt, 30)
        st.session_state.generated_image = (
            generated_image  # Store the generated image in session state
        )

    if st.session_state.generated_image:
        generated_image = st.session_state.generated_image
        grayscale_image, dithered_image = preper_image(generated_image)

        col1, col2 = st.columns(2)
        with col1:
            st.image(grayscale_image, caption="Original Image")
        with col2:
            st.image(dithered_image, caption="Resized and Dithered Image")

        col3, col4 = st.columns(2)
        with col3:
            if st.button("Print Original Image"):
                print_image(grayscale_image)
                st.success("Original image sent to printer!")
        with col4:
            if st.button("Print Dithered Image"):
                print_image(grayscale_image, dither=True)
                st.success("Dithered image sent to printer!")

    # Update last prompt
    st.session_state.last_prompt = prompt

# webcam
with tab4:
    st.subheader(":printer: a snapshot")
    on = st.toggle("ask user for camera permission")
    if on:
        picture = st.camera_input("Take a picture")
        if picture is not None:
            picture = Image.open(picture).convert("RGB")
            grayscale_image, dithered_image = preper_image(picture)

            st.image(dithered_image, caption="Resized and Dithered Image")

            # Save webcam image before printing
            filename = safe_filename("webcam")
            file_path = os.path.join(label_dir, filename)
            picture.save(file_path, "PNG")
            st.success(f"Webcam photo saved as {filename}")

            # print options
            colc, cold = st.columns(2)
            with colc:
                if st.button("Print rotated Image"):
                    print_image(grayscale_image, rotate=90, dither=True)
                    st.balloons()
                    st.success("rotated image sent to printer!")
            with cold:
                if st.button("Print Image"):
                    print_image(grayscale_image, dither=True)
                    st.success("image sent to printer!")

# cat
with tab5:
    st.subheader(":printer: a cat")
    st.caption("from the fine folks at https://thecatapi.com/")
    
    # Check if Cat API key exists and is valid
    cat_api_key = st.secrets.get("cat_api_key", "")
    
    if not cat_api_key or cat_api_key == "ask me":
        st.warning("⚠️ Cat API key is not configured")
        st.info("""
        To enable the Cat API feature:
        1. Get a free API key from [TheCatAPI](https://thecatapi.com/)
        2. Add your key to `.streamlit/secrets.toml`:
        ```toml
        cat_api_key = "your_api_key_here"
        ```
        """)
    else:
        if st.button("Fetch cat"):
            try:
                caturl = "https://api.thecatapi.com/v1/images/search"
                api_url = f"{caturl}?limit=1&type=static&api_key={cat_api_key}"
                response = requests.get(api_url)
                response.raise_for_status()  # Raise an exception for bad status codes
                data = response.json()

                # Extract image URL from JSON
                image_url = data[0]["url"]

                # Fetch the image
                image_response = requests.get(image_url)
                image_response.raise_for_status()
                img = Image.open(io.BytesIO(image_response.content))
                
                # Process and display the image
                grayscale_image, dithered_image = preper_image(img)
                st.image(dithered_image, caption="Fetched Cat Image")
                
                if st.button("Print Cat"):
                    print_image(grayscale_image, dither=True)
                    st.success("Cat sent to printer!")
                    
            except Exception as e:
                st.error(f"Error fetching cat: {str(e)}")

# history tab
with tab6:
    st.subheader("Gallery of Labels and Stickers")
    
    # Initialize session state variables if they don't exist
    if 'saved_images_list' not in st.session_state:
        st.session_state.saved_images_list = list_saved_images()
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    if 'filter_duplicates' not in st.session_state:
        st.session_state.filter_duplicates = True
    
    # Get pagination settings from secrets with defaults
    items_per_page = st.secrets.get("items_per_page", 5)  # Default to 3x3 grid
    
    # Search, filter, and refresh controls
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search_query = st.text_input("Search filenames", value=st.session_state.search_query)
    with col2:
        filter_duplicates = st.checkbox("Filter duplicates", value=st.session_state.filter_duplicates)
        st.session_state.filter_duplicates = filter_duplicates
    with col3:
        if st.button("Refresh Gallery"):
            st.session_state.saved_images_list = list_saved_images(filter_duplicates)
            st.session_state.page_number = 0
            st.rerun()

    # Update image list if filter setting changed
    if filter_duplicates != st.session_state.filter_duplicates:
        st.session_state.saved_images_list = list_saved_images(filter_duplicates)
        st.session_state.page_number = 0
        st.rerun()

    # Filter images based on search query
    filtered_images = [
        img for img in st.session_state.saved_images_list 
        if search_query.lower() in os.path.basename(img).lower()
    ]

    # Pagination
    total_pages = max((len(filtered_images) - 1) // items_per_page + 1, 1)
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Previous", disabled=st.session_state.page_number <= 0):
            st.session_state.page_number -= 1
            st.rerun()
    with col2:
        st.write(f"Page {st.session_state.page_number + 1} of {total_pages}")
    with col3:
        if st.button("Next", disabled=st.session_state.page_number >= total_pages - 1):
            st.session_state.page_number += 1
            st.rerun()

    # Calculate start and end indices for current page
    start_idx = st.session_state.page_number * items_per_page
    end_idx = min(start_idx + items_per_page, len(filtered_images))
    
    # Display current page images
    cols_per_row = 3
    current_page_images = filtered_images[start_idx:end_idx]
    
    # Show total count of filtered images
    st.caption(f"Showing {len(current_page_images)} of {len(filtered_images)} images")

    # Display images in grid
    for i in range(0, len(current_page_images), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            idx = i + j
            if idx < len(current_page_images):
                with cols[j]:
                    image_path = current_page_images[idx]
                    image = Image.open(image_path)
                    st.image(image, use_column_width=True)

                    filename = os.path.basename(image_path)
                    modified_time = datetime.fromtimestamp(
                        os.path.getmtime(image_path)
                    ).strftime("%Y-%m-%d %H:%M")
                    st.caption(f"{filename}\n{modified_time}")

                    if st.button(f"Print", key=f"print_{idx}_{st.session_state.page_number}"):
                        print_image(image, dither=True)
                        st.success("Sent to printer!")

# faq
with tab7:
    st.subheader("FAQ:")
    st.markdown(
        """
        *dithering* is suggested (sometimes inforced) if source is not lineart as grayscale and color look bad at thermal printer

        all uploaded images and generated labels are saved
        uploaded camera snapshot are NOT saved, only printed.

        app [code](https://github.com/5shekel/printit)

        PRINT ALOT is the best!
        """
    )
    st.image(Image.open("assets/station_sm.jpg"), caption="TAMI printshop")
