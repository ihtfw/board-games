import json
import math
import os
from PIL import Image, ImageDraw

ASSETS_DIR = "assets"
OUTPUT_DIR = "output"

# A4 in mm
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
MM_PER_INCH = 25.4


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def center_crop_to_ratio(img, target_w, target_h):
    """Center-crop image to match target aspect ratio."""
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if abs(src_ratio - target_ratio) < 0.001:
        return img

    if src_ratio > target_ratio:
        # Source is wider — crop width
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        return img.crop((left, 0, left + new_w, src_h))
    else:
        # Source is taller — crop height
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        return img.crop((0, top, src_w, top + new_h))


def process_image(filepath, target_w, target_h):
    """Center-crop and resize image to target dimensions."""
    img = Image.open(filepath).convert("RGBA")
    img = center_crop_to_ratio(img, target_w, target_h)
    img = img.resize((target_w, target_h), Image.LANCZOS)
    return img


def mm_to_px(mm, dpi):
    return int(mm / MM_PER_INCH * dpi)


def compose_a4_pages(tiles, config):
    dpi = config["dpi"]
    target_w = mm_to_px(config["width_mm"], dpi)
    target_h = mm_to_px(config["height_mm"], dpi)
    sp_x = mm_to_px(config["spacing_mm"]["x"], dpi)
    sp_y = mm_to_px(config["spacing_mm"]["y"], dpi)

    # Convert A4 to pixels
    a4_w = mm_to_px(A4_WIDTH_MM, dpi)
    a4_h = mm_to_px(A4_HEIGHT_MM, dpi)

    # How many tiles fit per page
    cols = max(1, (a4_w + sp_x) // (target_w + sp_x))
    rows = max(1, (a4_h + sp_y) // (target_h + sp_y))
    per_page = cols * rows

    # Center the grid on the page
    grid_w = cols * target_w + (cols - 1) * sp_x
    grid_h = rows * target_h + (rows - 1) * sp_y
    offset_x = (a4_w - grid_w) // 2
    offset_y = (a4_h - grid_h) // 2

    total_pages = math.ceil(len(tiles) / per_page)

    print(f"A4 page: {a4_w}x{a4_h} px at {dpi} DPI")
    print(f"Tile size: {target_w}x{target_h} px")
    print(f"Grid: {cols} cols x {rows} rows = {per_page} per page")
    print(f"Total tiles: {len(tiles)}, pages: {total_pages}")

    pages = []
    for page_idx in range(total_pages):
        page = Image.new("RGB", (a4_w, a4_h), (255, 255, 255))
        start = page_idx * per_page
        page_tiles = tiles[start : start + per_page]

        for i, tile in enumerate(page_tiles):
            col = i % cols
            row = i // cols
            x = offset_x + col * (target_w + sp_x)
            y = offset_y + row * (target_h + sp_y)
            page.paste(tile, (x, y), tile if tile.mode == "RGBA" else None)

        # Draw dashed cut lines across the full page
        draw = ImageDraw.Draw(page)
        line_color = (180, 180, 180)
        dash = mm_to_px(2, dpi)
        gap = mm_to_px(2, dpi)

        def draw_dashed_hline(y):
            x = 0
            while x < a4_w:
                draw.line([(x, y), (min(x + dash, a4_w), y)], fill=line_color)
                x += dash + gap

        def draw_dashed_vline(x):
            y = 0
            while y < a4_h:
                draw.line([(x, y), (x, min(y + dash, a4_h))], fill=line_color)
                y += dash + gap

        # Horizontal lines along top/bottom edges of each row
        for row in range(rows + 1):
            if row < rows:
                y = offset_y + row * (target_h + sp_y)
            else:
                y = offset_y + (rows - 1) * (target_h + sp_y) + target_h
            draw_dashed_hline(y)

        # Vertical lines along left/right edges of each column
        for col in range(cols + 1):
            if col < cols:
                x = offset_x + col * (target_w + sp_x)
            else:
                x = offset_x + (cols - 1) * (target_w + sp_x) + target_w
            draw_dashed_vline(x)

        pages.append(page)

    return pages


def main():
    config = load_config()
    dpi = config["dpi"]
    target_w = mm_to_px(config["width_mm"], dpi)
    target_h = mm_to_px(config["height_mm"], dpi)

    # Known top-level keys that are not image entries
    meta_keys = {"width_mm", "height_mm", "dpi", "spacing_mm"}

    # Build flat list of tiles
    tiles = []
    for key, entry in config.items():
        if key in meta_keys:
            continue
        filepath = os.path.join(ASSETS_DIR, entry["file"])
        count = entry["count"]
        print(f"Processing {key}: {entry['file']} x{count}")
        img = process_image(filepath, target_w, target_h)
        tiles.extend([img] * count)

    pages = compose_a4_pages(tiles, config)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for i, page in enumerate(pages):
        out_path = os.path.join(OUTPUT_DIR, f"page_{i + 1:02d}.png")
        page.save(out_path, dpi=(config["dpi"], config["dpi"]))
        print(f"Saved {out_path}")

    print("Done!")


if __name__ == "__main__":
    main()
