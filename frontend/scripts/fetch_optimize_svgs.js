// Script: fetch_optimize_svgs.js
// Usage: node fetch_optimize_svgs.js urls.txt
// - urls.txt should contain one SVG URL per line and target filenames as: url,filename.svg
// Requires: npm i node-fetch@2 svgo@2

const fs = require('fs');
const path = require('path');
const fetch = require('node-fetch');
const { optimize } = require('svgo');

async function download(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to download ${url}: ${res.status}`);
  return await res.text();
}

async function run() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error('Usage: node fetch_optimize_svgs.js urls.txt');
    process.exit(1);
  }

  const listFile = args[0];
  const data = fs.readFileSync(listFile, 'utf8').split(/\r?\n/).map(l=>l.trim()).filter(Boolean);
  const outDir = path.join(__dirname, '..', 'src', 'assets', 'illustrations');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  for (const line of data) {
    // line format: url,filename.svg
    const [url, filename] = line.split(',').map(s => s.trim());
    if (!url || !filename) {
      console.warn('Skipping invalid line:', line);
      continue;
    }

    console.log('Downloading', url);
    try {
      const svg = await download(url);
      console.log('Optimizing', filename);
      const optimized = optimize(svg, { path: filename, multipass: true });
      const outPath = path.join(outDir, filename);
      fs.writeFileSync(outPath, optimized.data, 'utf8');
      console.log('Saved', outPath);
    } catch (e) {
      console.error('Error fetching', url, e.message);
    }
  }
}

run();
