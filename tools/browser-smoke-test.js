/**
 * 无头浏览器冒烟测试：用 Chrome DevTools Protocol 直接驱动游戏页面。
 *
 * 用法：node tools/browser-smoke-test.js
 *      （找不到 Chrome 时用 CHROME_PATH 环境变量指定浏览器路径）
 *
 * 目的不是"看起来对"，而是拿到硬证据：
 *   1. 页面有没有 JS 报错
 *   2. canvas 是否真的是正方形（尺寸对齐）
 *   3. HUD 标签有没有溢出换行
 *   4. AI 模式能不能真的跑起来、有没有画出路径
 *   5. 网页版压测能不能出结果、和命令行版结论是否一致
 * 零依赖：用 Node 22 自带的 fetch 和 WebSocket 直接说 CDP，
 * 不需要装 puppeteer / playwright。
 */
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

/* 自动寻找本机 Chrome / Edge；也可以用 CHROME_PATH 环境变量手动指定 */
function findBrowser() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidates = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium'
  ];
  const hit = candidates.find(p => { try { return fs.statSync(p).isFile(); } catch (e) { return false; } });
  if (!hit) {
    console.error('没找到 Chrome / Edge，请设置环境变量 CHROME_PATH 指向浏览器可执行文件。');
    process.exit(2);
  }
  return hit;
}

const CHROME = findBrowser();
// 被测页面：默认本仓库的 game/index.html，也可以用第一个命令行参数指定
const PAGE = process.argv[2] || path.join(__dirname, '..', 'game', 'index.html');
const URL = 'file:///' + path.resolve(PAGE).replace(/\\/g, '/');
const PORT = 9333;

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'cdp-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  '--remote-debugging-port=' + PORT,
  '--user-data-dir=' + profile,
  '--window-size=1180,1100',
  URL
], { stdio: 'ignore' });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

let ws, msgId = 0;
const pending = new Map();
const consoleErrors = [];
const pageErrors = [];

function send(method, params) {
  const id = ++msgId;
  ws.send(JSON.stringify({ id, method, params: params || {} }));
  return new Promise((res, rej) => pending.set(id, { res, rej }));
}

async function evalJs(expr) {
  const r = await send('Runtime.evaluate', {
    expression: expr, returnByValue: true, awaitPromise: true
  });
  if (r.exceptionDetails) throw new Error('页面内异常: ' + r.exceptionDetails.text);
  return r.result.value;
}

(async () => {
  // 等 DevTools 端点起来
  let target = null;
  for (let i = 0; i < 40 && !target; i++) {
    await sleep(250);
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      target = list.find(t => t.type === 'page' && t.url.startsWith('file:'));
    } catch (e) {}
  }
  if (!target) throw new Error('连不上 Chrome 调试端口');

  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));

  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { res, rej } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      return;
    }
    if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
      consoleErrors.push(m.params.type + ': ' + m.params.args.map(a => a.value || a.description).join(' '));
    }
    if (m.method === 'Runtime.exceptionThrown') {
      pageErrors.push(m.params.exceptionDetails.text + ' ' +
        (m.params.exceptionDetails.exception && m.params.exceptionDetails.exception.description || ''));
    }
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
      pageErrors.push('LOG: ' + m.params.entry.text);
    }
  });

  await send('Runtime.enable');
  await send('Log.enable');
  await send('Page.enable');
  await sleep(800);

  const out = {};

  /* ---- 1. 基本环境 ---- */
  out.title = await evalJs('document.title');
  out.coreLoaded = await evalJs('typeof window.SnakeCore === "object" && window.SnakeCore.COLS');
  out.canvas = await evalJs(`(() => {
    const c = document.getElementById('board');
    const r = c.getBoundingClientRect();
    return { cssW: Math.round(r.width), cssH: Math.round(r.height),
             bufW: c.width, bufH: c.height, square: Math.abs(r.width - r.height) < 1.5 };
  })()`);

  /* ---- 2. HUD 标签是否溢出 ---- */
  out.hudOverflow = await evalJs(`[...document.querySelectorAll('.hud .k')]
    .filter(e => e.scrollWidth > e.clientWidth + 1)
    .map(e => e.textContent)`);

  /* ---- 3. 切到 AI 模式并跑一会儿 ---- */
  await evalJs('document.getElementById("btn-ai").click()');
  await sleep(2200);
  out.ai = await evalJs(`({
    status: document.getElementById('hud-score').textContent,
    target: document.getElementById('hud-target').textContent,
    note: document.getElementById('now-note').textContent,
    logLines: document.querySelectorAll('#log li').length,
    firstLog: (document.querySelector('#log li') || {}).textContent || '',
    aiButtonOn: document.getElementById('btn-ai').classList.contains('on')
  })`);

  await sleep(2500);
  out.aiLater = await evalJs(`({
    score: document.getElementById('hud-score').textContent,
    note: document.getElementById('now-note').textContent
  })`);

  /* ---- 4. 暂停一下，避免干扰压测 ---- */
  await evalJs('document.getElementById("btn-start").click()');

  /* ---- 5. 点击「跑 30 局」等结果 ---- */
  await evalJs('document.getElementById("btn-stress").click()');
  let stressText = '';
  for (let i = 0; i < 60; i++) {
    await sleep(500);
    stressText = await evalJs('document.getElementById("stress-out").textContent');
    if (stressText.includes('达标率')) break;
  }
  out.stress = stressText;

  /* ---- 6. 深色主题下画布会不会报错 ---- */
  await evalJs('document.getElementById("theme-switch").checked = true; document.getElementById("theme-switch").dispatchEvent(new Event("change"))');
  await sleep(400);
  out.darkOk = await evalJs('document.getElementById("theme-switch").checked');

  console.log('================= 冒烟测试结果 =================');
  console.log('页面标题          ' + out.title);
  console.log('核心逻辑已加载    ' + (out.coreLoaded ? '是（COLS=' + out.coreLoaded + '）' : '否 ✗'));
  console.log('canvas            CSS ' + out.canvas.cssW + '×' + out.canvas.cssH +
              ' / 缓冲区 ' + out.canvas.bufW + '×' + out.canvas.bufH +
              ' / 正方形 ' + (out.canvas.square ? '是' : '否 ✗'));
  console.log('HUD 溢出标签      ' + (out.hudOverflow.length ? out.hudOverflow.join(' , ') + ' ✗' : '无'));
  console.log('AI 模式按钮高亮   ' + out.ai.aiButtonOn);
  console.log('AI 2.2 秒后       ' + out.ai.status + ' 分 · ' + out.ai.target + ' · 日志 ' + out.ai.logLines + ' 条');
  console.log('  最新决策        ' + out.aiLater.note);
  console.log('AI 再跑 2.5 秒    ' + out.aiLater.score + ' 分');
  console.log('深色主题切换      ' + (out.darkOk ? 'OK' : '失败 ✗'));
  console.log('--- 网页版压测输出 ---');
  console.log(out.stress.trim());
  console.log('--- JS 报错 ---');
  console.log(pageErrors.length ? pageErrors.join('\n') : '无');
  console.log('--- console 警告/错误 ---');
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '无');
  console.log('================================================');

  ws.close();
  chrome.kill();
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
  process.exit(0);
})().catch(e => {
  console.error('测试失败: ' + e.message);
  try { chrome.kill(); } catch (_) {}
  process.exit(1);
});
