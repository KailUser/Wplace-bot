import qrcode
from PIL import Image

# Target URL
url = "https://discord.gg/jcCYvvqXVw"

# Generate a basic QR Code
qr = qrcode.QRCode(
    version=1,  # smallest possible version (21x21 before resizing)
    error_correction=qrcode.constants.ERROR_CORRECT_L,  # lowest error correction = more data fit
    box_size=1,  # tiny tiny boxes
    border=0,  # no border because 16x16 can't afford that
)
qr.add_data(url)
qr.make(fit=True)

# Convert to PIL image
img = qr.make_image(fill_color="black", back_color="white").convert("L")

# Resize down to 16x16
tiny = img.resize((42, 42), Image.NEAREST)

# Save or show
tiny.save("qr16x16.png")
tiny.show()
