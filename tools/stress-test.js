/*!
 * stress-test.js — AI 自动玩压测脚本（Node 运行，无浏览器）
 *
 * 用法：
 *   node tools/stress-test.js          # 默认跑 100 局
 *   node tools/stress-test.js 500      # 跑 500 局
 *
 * 它直接复用 game/snake-core.js 里的同一套规则和 AI，所以测出来的成功率
 * 就是网页里那个 AI 的真实水平，不是另外写的一份「理想情况」代码。
 */

const path = require('path');
const core = require(path.join(__dirname, '..', 'game', 'snake-core.js'));

const GAMES = Number(process.argv[2] || 100);
const MAX_STEPS = 4000;
const TARGET = core.TARGET_SCORE;   // 15

const scores = [];
let reached = 0;      // 达到「连续吃满 15 个」的局数
let lastStepEnd = 0;

console.log('贪吃蛇 AI 压测 · 棋盘 %d×%d · 目标：连续吃满 %d 个不放死', core.COLS, core.ROWS, TARGET);
console.log('规则与网页版共用 game/snake-core.js，逐局完整模拟，无可视化开销。');
console.log('');

const t0 = Date.now();
for (let i = 0; i < GAMES; i++) {
  const r = core.playOneGame(MAX_STEPS);
  scores.push(r.score);
  if (r.score >= TARGET) reached++;
  if (r.steps >= MAX_STEPS) lastStepEnd++;
}

const ms = Date.now() - t0;
const sum = scores.reduce((a, b) => a + b, 0);
const sorted = scores.slice().sort((a, b) => a - b);
const median = sorted[Math.floor(sorted.length / 2)];
const best = sorted[sorted.length - 1];
const worst = sorted[0];

const pct = (n) => ((n / GAMES) * 100).toFixed(1) + '%';

console.log('局数            ' + GAMES);
console.log('达标局数(≥' + TARGET + ')   ' + reached);
console.log('达标成功率      ' + pct(reached));
console.log('平均得分        ' + (sum / GAMES).toFixed(2));
console.log('中位数得分      ' + median);
console.log('最高 / 最低     ' + best + ' / ' + worst);
console.log('总步数          ' + scores.length + ' 局共 ' + (ms / 1000).toFixed(2) + ' 秒');
console.log('');

// 打印一张分数分布柱状图，方便直接贴进 README
const buckets = {};
for (const s of scores) {
  const b = s >= 60 ? '60+' : s >= TARGET ? TARGET + '-59' : s >= 10 ? '10-14' : '0-9';
  buckets[b] = (buckets[b] || 0) + 1;
}
const order = ['0-9', '10-14', TARGET + '-59', '60+'];
console.log('分数分布');
for (const b of order) {
  const n = buckets[b] || 0;
  console.log('  ' + b.padEnd(7) + ' ' + String(n).padStart(4) + '  ' + '#'.repeat(Math.round((n / GAMES) * 60)));
}
console.log('');
console.log('结论：' + (reached / GAMES >= 0.95
  ? '达标率 ' + pct(reached) + '，满足任务书要求的 AI 自动玩指标。'
  : '达标率 ' + pct(reached) + '，低于 95%，需要继续调参。'));
