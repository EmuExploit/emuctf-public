const { spawn } = require('child_process');
const path = require('path');

const children = [];
let shuttingDown = false;

function run(name, file) {
  const child = spawn(process.execPath, [path.join(__dirname, file)], {
    stdio: 'inherit',
    env: process.env,
  });
  child.on('exit', (code, signal) => {
    if (shuttingDown) return;
    console.error(`[supervisor] ${name} exited (code=${code} signal=${signal}); shutting down`);
    shutdown(code === 0 ? 1 : code || 1);
  });
  children.push(child);
  return child;
}

function shutdown(exitCode) {
  shuttingDown = true;
  for (const child of children) {
    if (!child.killed) child.kill('SIGTERM');
  }
  setTimeout(() => process.exit(exitCode), 500);
}

process.on('SIGTERM', () => shutdown(0));
process.on('SIGINT', () => shutdown(0));

run('internal-api', 'internal/server.js');
run('external-web', 'external/server.js');
