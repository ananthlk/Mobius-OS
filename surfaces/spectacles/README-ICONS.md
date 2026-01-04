# Chrome Extension Icon Setup

The extension needs PNG icon files for the browser toolbar. The SVG source file is `icon.svg`.

## Quick Setup (Recommended)

1. **Online Converter** (Easiest):
   - Go to https://svgtopng.com/ or https://convertio.co/svg-png/
   - Upload `icon.svg`
   - Generate and download these sizes:
     - `icon-16.png` (16×16px)
     - `icon-32.png` (32×32px)
     - `icon-48.png` (48×48px)
     - `icon-128.png` (128×128px)
   - Save all files in the `surfaces/spectacles/` directory

2. **Update manifest.json**:
   After creating the PNG files, uncomment the icon configuration in `manifest.json`:
   ```json
   "action": {
       "default_title": "Open Möbius Side Panel",
       "default_icon": {
           "16": "icon-16.png",
           "32": "icon-32.png",
           "48": "icon-48.png",
           "128": "icon-128.png"
       }
   },
   "icons": {
       "16": "icon-16.png",
       "32": "icon-32.png",
       "48": "icon-48.png",
       "128": "icon-128.png"
   },
   ```

3. **Reload Extension**:
   - Open `chrome://extensions/`
   - Click the reload button on your extension
   - The infinity symbol should now appear in the toolbar!

## Alternative Methods

### ImageMagick
```bash
convert -background none -resize 16x16 icon.svg icon-16.png
convert -background none -resize 32x32 icon.svg icon-32.png
convert -background none -resize 48x48 icon.svg icon-48.png
convert -background none -resize 128x128 icon.svg icon-128.png
```

### Inkscape
```bash
inkscape icon.svg --export-filename=icon-16.png --export-width=16 --export-height=16
inkscape icon.svg --export-filename=icon-32.png --export-width=32 --export-height=32
inkscape icon.svg --export-filename=icon-48.png --export-width=48 --export-height=48
inkscape icon.svg --export-filename=icon-128.png --export-width=128 --export-height=128
```

## Note

The extension will work without icons (it will use Chrome's default icon). The icons are optional but recommended for better branding.
