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

function checkEnvVars() {
  const services = {
    gemini: 'GEMINI_API_KEY',
    openai: 'OPENAI_API_KEY',
    claude: 'ANTHROPIC_API_KEY',
    deepseek: 'DEEPSEEK_API_KEY',
  };

  const service = process.env.AI_SERVICE || 'gemini';
  if (!services[service]) {
    console.error(`Invalid AI service: ${service}`);
    console.error('Valid options: ' + Object.keys(services).join(', '));
    process.exit(1);
  }

  const keyVar = services[service];
  if (!process.env[keyVar]) {
    console.warn(`Warning: ${keyVar} environment variable not set`);
    console.warn(
      `You will need to set it using: export ${keyVar}='your-api-key'`
    );
  }
}

async function main() {
  try {
    const isGlobalInstall = process.env.npm_config_global === 'true';
    const isDevelopment =
      process.env.NODE_ENV === 'development' || !isGlobalInstall;

    console.log(
      `Installing in ${isDevelopment ? 'development' : 'production'} mode...`
    );

    // Check environment variables
    checkEnvVars();

    if (!fs.existsSync(venvPath)) {
      console.log('Creating virtual environment...');
      await runCommand('python3', ['-m', 'venv', venvPath]);
    }

    const isWindows = process.platform === 'win32';
    const binDir = isWindows ? 'Scripts' : 'bin';
    const pythonPath = path.join(
      venvPath,
      binDir,
      isWindows ? 'python.exe' : 'python3'
    );
    const pipPath = path.join(venvPath, binDir, isWindows ? 'pip.exe' : 'pip');

    console.log('Installing Python package...');
    await runCommand(pythonPath, ['-m', 'pip', 'install', '--upgrade', 'pip']);
    await runCommand(pythonPath, [
      '-m',
      'pip',
      'install',
      '--upgrade',
      'setuptools',
      'wheel',
      'keyring',
    ]);

    // Install dev dependencies if in development mode
    if (isDevelopment) {
      console.log('Installing development dependencies...');
      await runCommand(pythonPath, [
        '-m',
        'pip',
        'install',
        '-r',
        path.join(packageRoot, 'requirements-dev.txt'),
      ]);
    }

    await runCommand(
      pythonPath,
      [
        '-m',
        'pip',
        'install',
        isDevelopment ? '-e' : '',
        packageRoot,
        '--no-cache-dir',
      ].filter(Boolean)
    );

    const pipConfigDir = path.join(venvPath, isWindows ? 'pip' : 'pip.conf');
    if (!fs.existsSync(pipConfigDir)) {
      fs.writeFileSync(
        pipConfigDir,
        '[global]\nbreak-system-packages = true\n'
      );
    }

    if (isGlobalInstall && !isDevelopment) {
      let npmGlobalPrefix;
      try {
        npmGlobalPrefix = execSync('npm config get prefix', {
          encoding: 'utf8',
        }).trim();
      } catch (error) {
        console.error('Failed to get npm global prefix:', error.message);
        process.exit(1);
      }

      console.log('Creating global command links...');
      const globalBinPath = isWindows
        ? npmGlobalPrefix
        : path.join(npmGlobalPrefix, 'bin');
      const commands = ['git-commit-assistant', 'gcommit'];
      const mainScriptPath = path.join(
        packageRoot,
        'bin',
        'git-commit-assistant'
      );

      for (const cmd of commands) {
        const cmdPath = path.join(globalBinPath, cmd);
        try {
          const scriptContent = fs.readFileSync(mainScriptPath, 'utf8');
          fs.writeFileSync(cmdPath, scriptContent);
          fs.chmodSync(cmdPath, '755');
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
