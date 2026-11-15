
from PIL import Image
from tkinter import Tk, filedialog, messagebox

WIDTH = 256
HEIGHT = 256
START_ADDRESS = 0x2000


def convert_image(input_file, output_file):
    # Open and resize image
    image = Image.open(input_file).convert("L")
    image = image.resize((WIDTH, HEIGHT))

    # Convert to pure black and white
    image = image.point(
        lambda p: 255 if p >= 128 else 0,
        mode="1"
    )

    pixels = image.load()
    words = []

    # Convert pixels into 16-bit words
    # Leftmost pixel = most significant bit
    for y in range(HEIGHT):
        for x in range(0, WIDTH, 16):
            word = 0

            for bit in range(16):
                word <<= 1

                if pixels[x + bit, y] == 255:
                    word |= 1

            words.append(word)

    # Group all addresses by their data value
    value_addresses = {}

    for i, word in enumerate(words):
        address = START_ADDRESS + i

        if word not in value_addresses:
            value_addresses[word] = []

        value_addresses[word].append(address)

    # Generate assembly
    assembly = []

    for word, addresses in value_addresses.items():
        # Load each unique value only once
        assembly.append(f"LDA {word:04X}")

        # Write it to every address that needs it
        for address in addresses:
            assembly.append(f"ATR {address:04X}")

    # Save assembly file
    with open(output_file, "w") as f:
        f.write("\n".join(assembly))

    # Statistics
    lda_count = len(value_addresses)
    atr_count = len(words)

    return lda_count, atr_count


def main():
    root = Tk()
    root.withdraw()

    # Select image
    input_file = filedialog.askopenfilename(
        title="Select an image",
        filetypes=[
            ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
            ("All files", "*.*")
        ]
    )

    if not input_file:
        root.destroy()
        return

    # Select output location
    output_file = filedialog.asksaveasfilename(
        title="Save assembly file",
        defaultextension=".asm",
        filetypes=[
            ("Assembly files", "*.asm"),
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
    )

    if not output_file:
        root.destroy()
        return

    try:
        lda_count, atr_count = convert_image(
            input_file,
            output_file
        )

        messagebox.showinfo(
            "Conversion complete",
            f"Image converted successfully!\n\n"
            f"Resolution: {WIDTH}x{HEIGHT}\n"
            f"Unique values (LDA): {lda_count}\n"
            f"Memory writes (ATR): {atr_count}\n"
            f"Total instructions: {lda_count + atr_count}\n\n"
            f"Saved to:\n{output_file}"
        )

    except Exception as e:
        messagebox.showerror(
            "Conversion error",
            str(e)
        )

    root.destroy()


if __name__ == "__main__":
    main()
