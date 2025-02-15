#!/usr/bin/env node

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const packageRoot = path.join(__dirname, '..');
const venvPath = path.join(os.homedir(), '.git-commit-assistant-venv');

function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(command, args, { ...options, stdio: 'inherit' });
    proc.on('close', (code) =>
      code === 0
        ? resolve()
        : reject(new Error(`Command failed with code ${code}`))
    );
    proc.on('error', reject);
  });
}

async function main() {
  try {
    // Create virtual environment
    if (!fs.existsSync(venvPath)) {
      console.log('Creating virtual environment...');
      await runCommand('python3', ['-m', 'venv', venvPath]);
    }

    // Determine the pip path based on OS
    const isWindows = process.platform === 'win32';
    const pipPath = path.join(
      venvPath,
      isWindows ? 'Scripts' : 'bin',
      isWindows ? 'pip.exe' : 'pip'
    );

    // Install package in development mode
    console.log('Installing Python package...');
    await runCommand(pipPath, ['install', '-e', packageRoot]);

    // Create pip.conf if it doesn't exist
    const pipConfigDir = path.join(venvPath, isWindows ? 'pip' : 'pip.conf');
    if (!fs.existsSync(pipConfigDir)) {
      fs.writeFileSync(
        pipConfigDir,
        '[global]\nbreak-system-packages = true\n'
      );
    }

    console.log('Installation completed successfully!');
  } catch (error) {
    console.error('Installation failed:', error.message);
    process.exit(1);
  }
}

main();
