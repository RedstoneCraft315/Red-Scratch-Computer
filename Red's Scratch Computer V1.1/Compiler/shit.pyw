from pillow import Image
import os

# ==========================================================
# CONFIG
# ==========================================================
IMAGE_FILE = "Untitlel.tif"    # exported from GIMP (layers merged as pages)
CHAR_HEIGHT = 16
CHAR_WIDTH  = 16
GAP_BETWEEN_CHARS = 5             # address gap between characters
START_ADDR = 0xFFFF
THRESHOLD = 128                   # brightness threshold for b/w
# ==========================================================


def row_to_hex(bits):
    """Convert list of 0/1 bits to 16-bit hex."""
    value = 0
    for b in bits:
        value = (value << 1) | b
    return f"{value:04X}"


def process_layer(img, layer_index):
    """Returns row patterns (top→bottom) as 16-bit hex strings."""
    w, h = img.size
    rows = []

    for y in range(h):
        bits = []
        for x in range(w):
            pixel = img.getpixel((x, y))
            pixel = pixel if isinstance(pixel, int) else pixel[0]
            bits.append(1 if pixel < THRESHOLD else 0)
        rows.append(row_to_hex(bits))

    return rows


def main():
    # Load image with layers
    im = Image.open(IMAGE_FILE)

    # If file has layers (GIMP’s multi-layer format)
    try:
        layers = []
        for i in range(im.n_frames):
            im.seek(i)
            layers.append(im.copy().convert("L"))
    except:
        print("This image does not contain multiple layers!")
        return

    addr = START_ADDR

    output_lines = []

    for li, layer in enumerate(layers):
        rows = process_layer(layer, li)

        # Reverse address order: bottom row = highest address
        for row_hex in reversed(rows):
            output_lines.append(f"STR {addr:04X} {row_hex}")
            addr -= 1

        # gap between characters
        for _ in range(GAP_BETWEEN_CHARS):
            addr -= 1

    # Print result
    print("\n".join(output_lines))


if __name__ == "__main__":
    main()
