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

    // Determine the pip and python paths based on OS
    const isWindows = process.platform === 'win32';
    const binDir = isWindows ? 'Scripts' : 'bin';
    const pipPath = path.join(venvPath, binDir, isWindows ? 'pip.exe' : 'pip');
    const pythonPath = path.join(
      venvPath,
      binDir,
      isWindows ? 'python.exe' : 'python3'
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

    // Create symlinks for commands
    console.log('Creating command links...');
    const binPath = path.join(packageRoot, 'bin');
    const commands = ['git-commit-assistant', 'ga'];

    for (const cmd of commands) {
      const cmdPath = path.join(binPath, cmd);
      // Create the bin directory if it doesn't exist
      if (!fs.existsSync(binPath)) {
        fs.mkdirSync(binPath, { recursive: true });
      }

      // Create the command file
      const cmdContent = `#!/usr/bin/env node
require('${path.join(packageRoot, 'bin/git-commit-assistant')}');`;

      fs.writeFileSync(cmdPath, cmdContent);
      fs.chmodSync(cmdPath, '755'); // Make executable
    }

    console.log('Installation completed successfully!');
  } catch (error) {
    console.error('Installation failed:', error.message);
    process.exit(1);
  }
}

main();
