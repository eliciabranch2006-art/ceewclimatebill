/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export", // static export — deploys as plain HTML/JS to Vercel/Netlify/GitHub Pages
  images: { unoptimized: true },
};

module.exports = nextConfig;
