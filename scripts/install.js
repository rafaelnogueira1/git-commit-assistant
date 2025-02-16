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
    const isGlobalInstall = process.env.npm_config_global === 'true';
    const isDevelopment =
      process.env.NODE_ENV === 'development' || !isGlobalInstall;

    console.log(
      `Installing in ${isDevelopment ? 'development' : 'production'} mode...`
    );

    // Create virtual environment
    if (!fs.existsSync(venvPath)) {
      console.log('Creating virtual environment...');
      await runCommand('python3', ['-m', 'venv', venvPath]);
    }

    // Determine the pip path based on OS
    const isWindows = process.platform === 'win32';
    const binDir = isWindows ? 'Scripts' : 'bin';
    const pipPath = path.join(venvPath, binDir, isWindows ? 'pip.exe' : 'pip');

    // Install package in development mode
    console.log('Installing Python package...');
    await runCommand(
      pipPath,
      ['install', isDevelopment ? '-e' : '', packageRoot].filter(Boolean)
    );

    // Create pip.conf if it doesn't exist
    const pipConfigDir = path.join(venvPath, isWindows ? 'pip' : 'pip.conf');
    if (!fs.existsSync(pipConfigDir)) {
      fs.writeFileSync(
        pipConfigDir,
        '[global]\nbreak-system-packages = true\n'
      );
    }

    // Only create global links if we're installing globally (not during development)
    if (isGlobalInstall && !isDevelopment) {
      // Get npm global bin directory
      let npmGlobalPrefix;
      try {
        npmGlobalPrefix = execSync('npm config get prefix', {
          encoding: 'utf8',
        }).trim();
      } catch (error) {
        console.error('Failed to get npm global prefix:', error.message);
        process.exit(1);
      }

      // Create global command links
      console.log('Creating global command links...');
      const globalBinPath = isWindows
        ? npmGlobalPrefix
        : path.join(npmGlobalPrefix, 'bin');
      const commands = ['git-commit-assistant', 'gcommit'];

      for (const cmd of commands) {
        const cmdPath = path.join(globalBinPath, cmd);
        try {
          fs.writeFileSync(
            cmdPath,
            '#!/usr/bin/env node\n' +
              'require("git-commit-assistant/bin/git-commit-assistant");'
          );
          fs.chmodSync(cmdPath, '755'); // Make executable
          console.log(`Created global command: ${cmd}`);
        } catch (error) {
          console.error(`Failed to create ${cmd} command:`, error.message);
          process.exit(1);
        }
      }
    }

    console.log(
      `Installation completed successfully in ${
        isDevelopment ? 'development' : 'production'
      } mode!`
    );
  } catch (error) {
    console.error('Installation failed:', error.message);
    process.exit(1);
  }
}

main();
