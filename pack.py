from PIL import Image
import os
import math
import json
import sys

def is_square_image(img):
    return img.size[0] == img.size[1]

def is_bright_pixel(pixel, threshold=150):
    # Check if pixel brightness is above the threshold
    brightness = max(pixel[:3])
    return brightness > threshold

ores = ["diamond_", "emerald_", "gold_", "iron_", "lapis_", "redstone_", "quartz_"]
glowies = ["glowstone", "lava"]

def process_texture(img, offset, square_size, albedo_map, emissive_map, gloss_map, leaves_map):
    convert = img.convert('RGBA')
    grassColor = (145/255, 189/255, 89/255, 255)
    waterColor = (63/255, 118/255, 228/255, 255)

    for y in range(min(img.size[1], square_size)):
        for x in range(min(img.size[0], square_size)):
            pixel = convert.getpixel((x, y))

            for ore in ores:
                if ore in img.filename.lower():
                    if is_bright_pixel(pixel):
                        emissive_map.putpixel((offset[0] + x, offset[1] + y), pixel)
                        gloss_map.putpixel((offset[0] + x, offset[1] + y), (0, 0, 0, 255))

            for glowy in glowies:
                if glowy in img.filename.lower():
                    emissive_map.putpixel((offset[0] + x, offset[1] + y), pixel)

            if "leaves" in img.filename.lower():
                leaves_map.putpixel((offset[0] + x, offset[1] + y), 255)  # White for leaves map
                resultPixel = tuple(int(round(c1 * c2)) for c1, c2 in zip(pixel, grassColor))
                albedo_map.putpixel((offset[0] + x, offset[1] + y), resultPixel)

            if "grass" in img.filename.lower() and "snow" not in img.filename.lower() and "overlay" not in img.filename.lower():
                overlayPath = img.filename.replace(".png", "_overlay.png")
                if os.path.exists(overlayPath):
                    with Image.open(overlayPath) as overlay:
                        convertOverlay = overlay.convert('RGBA')
                        overlayPixel = convertOverlay.getpixel((x, y))

                        if overlayPixel[3] > 0:
                            resultPixel = tuple(int(round(c1 * c2)) for c1, c2 in zip(overlayPixel, grassColor))
                            albedo_map.putpixel((offset[0] + x, offset[1] + y), resultPixel)
                else:
                    resultPixel = tuple(int(round(c1 * c2)) for c1, c2 in zip(pixel, grassColor))
                    albedo_map.putpixel((offset[0] + x, offset[1] + y), resultPixel)

            if "water" in img.filename.lower():
                resultPixel = tuple(int(round(c1 * c2)) for c1, c2 in zip(pixel, waterColor))
                albedo_map.putpixel((offset[0] + x, offset[1] + y), resultPixel)

            if "glass" in img.filename.lower():
                    gloss_map.putpixel((offset[0] + x, offset[1] + y), (0, 0, 0, 255))

def pack_png_images(input_folder, output_file, order_file, matchOrder):
    if matchOrder:
        # Read the order list from the JSON file
        with open(order_file) as json_file:
            order_list = json.load(json_file)
            png_files = [order_item + ".png" for order_item in order_list]
    else:
        files = os.listdir(input_folder)
        png_files = sorted([
            f for f in files 
            if f.lower().endswith(".png") 
            #and is_square_image(Image.open(os.path.join(input_folder, f))) 
            and not any(char.isdigit() for char in f)
        ])

    if not png_files:
        print("No suitable block files found.")
        return

    # Open the first image to get the size
    first_image_path = os.path.join(input_folder, png_files[0])
    with Image.open(first_image_path) as first_image:
        # Get the size of the first image
        width, height = first_image.size

        # Calculate the dimensions of the square
        total_images = len(png_files)
        square_size = int(math.ceil(math.sqrt(total_images)))

        # Round up to the closest power of two
        square_size = int(math.pow(2, math.ceil(math.log2(square_size))))

        # List to store the order of packed textures (without .png extension)
        order_list = []

        # Create maps
        albedo_map = Image.new("RGBA", (square_size * width, square_size * height))
        emissive_map = Image.new("RGB", (square_size * width, square_size * height), (0, 0, 0))
        gloss_map = Image.new("RGBA", (square_size * width, square_size * height), (0, 0, 0, 0))
        leaves_map = Image.new("L", (square_size * width, square_size * height), 0)

        # Paste each PNG image into the packed image
        for i, png_file in enumerate(png_files):
            png_path = os.path.join(input_folder, png_file)

            if not os.path.exists(png_path):
                #print(f"Warning: The following file does not exist and will be skipped: {png_path}")
                continue

            with Image.open(png_path) as img:
                # Calculate the position in the square grid
                row = i // square_size
                col = i % square_size

                # Paste the image into the correct position
                albedo_map.paste(img.crop((0, 0, square_size, square_size)), (col * width, row * height))

                # Add the filename (without .png extension) to the order list
                order_list.append(os.path.splitext(png_file)[0])

                # Process the texture for emissive and gloss maps
                process_texture(img, (col * width, row * height), square_size, albedo_map, emissive_map, gloss_map, leaves_map)

        # Save the order list to a JSON file
        if not matchOrder:
            with open(order_file, 'w') as json_file:
                json.dump(order_list, json_file)
            print(f"Order of packed textures saved to {order_file}")

        # Save maps
        albedo_map.save(output_file, "PNG")
        if not matchOrder:
            emissive_map.save("./emissive_map.png", "PNG")
            gloss_map.save("./gloss_map.png", "PNG")
            leaves_map.save("./leaves_map.png", "PNG")
        print(f"Packing complete and maps saved to {output_file}")

if __name__ == "__main__":
    # Specify the input folder and output file
    input_folder = "./block"
    alternative_folder = "./blocks"
    output_file = "./packed_image.png"
    order_file = "./order.json"

    # Check if the input folder exists, if not, try an alternative folder
    if not os.path.exists(input_folder):
        if os.path.exists(alternative_folder):
            input_folder = alternative_folder
        else:
            print(f"Error: No {input_folder} folder nor {alternative_folder} folder exists.")
            exit()

    if len(sys.argv) > 1:
        option = sys.argv[1]
    else:
        print('What do you want to do?')
        print('1) Build complete atlas from scratch')
        print('2) Build atlas that matches order.json')
        option = input()

    print(option)
    
    if option == "1":
        pack_png_images(input_folder, output_file, order_file, False)
    elif option == "2":
        if not os.path.exists(order_file):
            print("Can't match order because order.json not found. Exiting.")
            exit()
        pack_png_images(input_folder, output_file, order_file, True)
    else:
        print("No valid option selected. Exiting.")
        exit()
