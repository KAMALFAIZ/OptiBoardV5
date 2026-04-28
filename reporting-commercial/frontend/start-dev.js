#!/usr/bin/env node
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const vite = spawn('npx', ['vite'], {
  cwd: __dirname,
  stdio: 'inherit'
});

vite.on('error', (err) => {
  console.error('Failed to start vite:', err);
  process.exit(1);
});
