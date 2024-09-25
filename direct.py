import os
import usb.core
from brother_ql.conversion import convert
from brother_ql.backends import backend_factory
from brother_ql.raster import BrotherQLRaster, BrotherQLRasterError
from brother_ql.models import ModelsManager
from brother_ql.backends.helpers import send

def find_and_parse_printer():
    """
    Find a Brother QL printer, parse its identifier, and determine its model.
    
    Returns:
        dict: Printer information including identifier, model, and parsed details,
              or None if no printer is found.
    """
    model_manager = ModelsManager()

    for backend_name in ['pyusb', 'linux_kernel']:
        backend = backend_factory(backend_name)
        for printer in backend['list_available_devices']():
            identifier = printer['identifier']
            parts = identifier.split('/')
            
            if len(parts) < 4:
                continue  # Skip if the identifier doesn't have the expected format
            
            protocol = parts[0]
            device_info = parts[2]
            serial_number = parts[3]
            vendor_id, product_id = device_info.split(':')
            
            # Determine printer model
            model = 'QL-570'  # Default model
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
    
    return None  # No printer found

def print_label(printer_info, image_path, label_size):
    """
    Print a label using the specified printer and image.
    
    Args:
        printer_info (dict): The printer information
        image_path (str): Path to the image file
        label_size (str): Size of the label
    
    Returns:
        bool: True if printing was successful, False otherwise
    """
    qlr = BrotherQLRaster(printer_info['model'])
    instructions = convert(
        qlr=qlr,
        images=[image_path],
        label=label_size,
        rotate='auto',
        threshold=70,
        dither=False,
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
    except BrotherQLRasterError as e:
        if "Trying to switch the operating mode" in str(e):
            print("Note: Printer doesn't support mode switching. This is normal for some models.")
            return True
        raise

def main():
    printer_info = find_and_parse_printer()
    if not printer_info:
        print("No Brother QL printer found. Please check the connection and try again.")
        return

    print(f"Found printer: {printer_info['identifier']} using {printer_info['backend']} backend")
    print(f"Detected printer model: {printer_info['model']}")

    for key in ['protocol', 'vendor_id', 'product_id', 'serial_number']:
        print(f"{key.capitalize()}: {printer_info[key]}")

    image_path = os.path.expanduser('temp/txt2img_2024-09-25_18-24-47.png')
    label_size = '62'

    if print_label(printer_info, image_path, label_size):
        print("Label printed successfully!")
    else:
        print("Printing failed.")

if __name__ == "__main__":
    main()
