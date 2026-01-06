#!/usr/bin/env node
/**
 * Generate PNG icons from SVG for Chrome extension
 * 
 * This script requires one of:
 * - puppeteer (npm install puppeteer)
 * - sharp (npm install sharp)
 * - Or use an online tool like: https://svgtopng.com/
 * 
 * For now, this script provides instructions and creates placeholder files
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const sizes = [16, 32, 48, 128];

console.log('🔷 Möbius Extension Icon Generator\n');
console.log('To generate PNG icons from icon.svg, you have several options:\n');

console.log('OPTION 1: Online Tool (Easiest)');
console.log('  1. Go to https://svgtopng.com/ or https://convertio.co/svg-png/');
console.log('  2. Upload surfaces/spectacles/icon.svg');
console.log('  3. Download and save as:');
sizes.forEach(size => {
  console.log(`     - icon-${size}.png (${size}x${size}px)`);
});

console.log('\nOPTION 2: ImageMagick (if installed)');
console.log('  Run these commands:');
sizes.forEach(size => {
  console.log(`  convert -background none -resize ${size}x${size} icon.svg icon-${size}.png`);
});

console.log('\nOPTION 3: Inkscape (if installed)');
sizes.forEach(size => {
  console.log(`  inkscape icon.svg --export-filename=icon-${size}.png --export-width=${size} --export-height=${size}`);
});

console.log('\nOPTION 4: Using sharp (npm install sharp)');
console.log('  Then run: node generate-icons-sharp.mjs\n');

// Check if icon.svg exists
const svgPath = path.join(__dirname, 'icon.svg');
if (!fs.existsSync(svgPath)) {
  console.error('❌ icon.svg not found!');
  process.exit(1);
}

console.log('✅ icon.svg found');
console.log('\nAfter generating the PNG files, the manifest.json will automatically use them.\n');



