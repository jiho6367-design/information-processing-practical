import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

const bundledNode = join(
  homedir(),
  '.cache',
  'codex-runtimes',
  'codex-primary-runtime',
  'dependencies',
  'node',
  'bin',
  process.platform === 'win32' ? 'node.exe' : 'node',
);

const nodeBinary = existsSync(bundledNode) ? bundledNode : process.execPath;
const viteEntry = join('node_modules', 'vite', 'bin', 'vite.js');
const result = spawnSync(nodeBinary, [viteEntry, 'build'], {
  stdio: 'inherit',
  env: {
    ...process.env,
    NODE_OPTIONS: `${process.env.NODE_OPTIONS ?? ''} --max-old-space-size=4096`.trim(),
  },
});

process.exit(result.status ?? 1);
