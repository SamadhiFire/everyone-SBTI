#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import net from "node:net";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key.startsWith("--") || value == null) {
      continue;
    }
    args[key.slice(2)] = value;
    i += 1;
  }
  return args;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getFreePort() {
  return await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        reject(new Error("free-port-unavailable"));
        return;
      }
      const { port } = address;
      server.close(() => resolve(port));
    });
    server.on("error", reject);
  });
}

async function waitForJson(url, attempts = 50) {
  let lastError = null;
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return await response.json();
      }
      lastError = new Error(`http-${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(200);
  }
  throw lastError ?? new Error("browser-debug-endpoint-unavailable");
}

class CdpClient {
  constructor(socket) {
    this.socket = socket;
    this.sequence = 0;
    this.pending = new Map();
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          pending.reject(new Error(JSON.stringify(message.error)));
        } else {
          pending.resolve(message.result);
        }
      }
    });
  }

  send(method, params = {}, sessionId = null) {
    const id = ++this.sequence;
    const payload = { id, method, params };
    if (sessionId) {
      payload.sessionId = sessionId;
    }
    this.socket.send(JSON.stringify(payload));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }
}

function ensureAbsolutePath(value, label) {
  if (!value) {
    throw new Error(`missing-${label}`);
  }
  return path.resolve(value);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputPath = ensureAbsolutePath(args.input, "input");
  const outputPath = ensureAbsolutePath(args.output, "output");
  const browserPath = ensureAbsolutePath(args.browser, "browser");
  const width = Number.parseInt(args.width ?? "1440", 10);
  const height = Number.parseInt(args.height ?? "960", 10);
  const profileDir = ensureAbsolutePath(
    args["profile-dir"] ?? path.join(os.tmpdir(), `everyone-s-sbti-${Date.now()}`),
    "profile-dir",
  );

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.mkdirSync(profileDir, { recursive: true });

  const port = await getFreePort();
  const browser = spawn(
    browserPath,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--allow-file-access-from-files",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${profileDir}`,
      "about:blank",
    ],
    {
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    },
  );

  let browserClosed = false;
  browser.on("exit", () => {
    browserClosed = true;
  });

  let socket;
  try {
    const version = await waitForJson(`http://127.0.0.1:${port}/json/version`);
    socket = new WebSocket(version.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });

    const cdp = new CdpClient(socket);
    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });

    await cdp.send("Page.enable", {}, sessionId);
    await cdp.send("Runtime.enable", {}, sessionId);
    await cdp.send(
      "Emulation.setDeviceMetricsOverride",
      {
        width,
        height,
        deviceScaleFactor: 1,
        mobile: false,
      },
      sessionId,
    );
    await cdp.send("Page.navigate", { url: pathToFileURL(inputPath).href }, sessionId);
    await sleep(1500);
    await cdp.send(
      "Runtime.evaluate",
      {
        expression: `
          (async () => {
            const report = document.getElementById('reportCapture');
            if (!report) {
              throw new Error('reportCapture-missing');
            }
            document.querySelectorAll('[data-export-hide]').forEach((node) => {
              node.style.display = 'none';
            });
            const images = Array.from(report.querySelectorAll('img'));
            await Promise.all(images.map((img) => {
              if (img.complete) {
                return typeof img.decode === 'function' ? img.decode().catch(() => {}) : Promise.resolve();
              }
              return new Promise((resolve) => {
                img.addEventListener('load', resolve, { once: true });
                img.addEventListener('error', resolve, { once: true });
              });
            }));
            const rect = report.getBoundingClientRect();
            return {
              x: rect.left + window.scrollX,
              y: rect.top + window.scrollY,
              width: Math.ceil(rect.width),
              height: Math.ceil(rect.height),
            };
          })();
        `,
        awaitPromise: true,
        returnByValue: true,
      },
      sessionId,
    ).then(async (result) => {
      const clip = {
        x: result.result.value.x,
        y: result.result.value.y,
        width: result.result.value.width,
        height: result.result.value.height,
        scale: 2,
      };
      const screenshot = await cdp.send(
        "Page.captureScreenshot",
        {
          format: "png",
          fromSurface: true,
          captureBeyondViewport: true,
          clip,
        },
        sessionId,
      );
      fs.writeFileSync(outputPath, Buffer.from(screenshot.data, "base64"));
    });

    await cdp.send("Target.closeTarget", { targetId });
    socket.close();
  } finally {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
    if (!browserClosed) {
      browser.kill();
    }
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
