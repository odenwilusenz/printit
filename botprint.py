from flask import Flask, request, jsonify
from PIL import Image
import tempfile, sys, subprocess

def detect_image_type(image):
    if image.mode == 'L':
        return 'Grayscale'
    elif image.mode == 'RGB':
        # Convert to grayscale for easier analysis
        grayscale_image = image.convert("L")
        pixel_values = list(grayscale_image.getdata())
        unique_values = len(set(pixel_values))
        
        if unique_values < 4:
            return 'Line Art'
        else:
            return 'Color'
    elif image.mode == '1':
        return 'Black and White'
    else:
        return 'Unknown'

def resize_and_dither(image):
    new_width = 696
    aspect_ratio = image.width / image.height
    new_height = int(new_width / aspect_ratio)
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)
    resized_grayscale_image = resized_image.convert("L")
    dithered_image = resized_grayscale_image.convert("1", dither=Image.FLOYDSTEINBERG)
    return resized_grayscale_image, dithered_image



def print_image(image):
    print("Starting print_image function")
    
    # Save the original image
    with tempfile.NamedTemporaryFile(suffix="_original.png", delete=False) as temp_file:
        original_file_path = temp_file.name
        image.save(original_file_path, "PNG")
        print(f"Saved original image to {original_file_path}")

    # Initialize a flag to track if any edits are made
    edited = False
    
    # Rotate the image if width > height
    if image.width > image.height:
        image = image.rotate(90, expand=True)
        edited = True
    
    image_type = detect_image_type(image)
    if image_type in ['Grayscale', 'Color', 'Line Art']:
        resized_grayscale_image, dithered_image = resize_and_dither(image)
        image = dithered_image  # Use the dithered image for further processing
        edited = True
    
    # Save the final image with appropriate suffix if edited
    suffix = "_edit" if edited else ""
    with tempfile.NamedTemporaryFile(suffix=f"{suffix}.png", delete=False) as temp_file:
        temp_file_path = temp_file.name
        image.save(temp_file_path, "PNG")
        print(f"Saved final image to {temp_file_path}")

    command = f"brother_ql -b pyusb --model QL-570 -p usb://0x04f9:0x2028/000M6Z401370 print -l 62 \"{temp_file_path}\""
    print(f"Running command: {command}")

    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print(result.stdout)
    print(result.stderr, file=sys.stderr)

    if "Device not found" in result.stderr:
        raise Exception("Device not found")

    if result.returncode != 0:
        raise Exception(f"Command failed with error: {result.stderr.strip()}")

    print(f"Finished print_image function for image: {temp_file_path}")


app = Flask(__name__)

@app.route('/api/print/image', methods=['POST'])
def api_print_image():
    try:
        image_file = request.files['image']
        image = Image.open(image_file.stream)
        print_image(image)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4678)