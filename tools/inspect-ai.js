/*!
 * inspect-ai.js — 逐步打印 AI 的决策过程（调试 / 讲解用）
 *
 * 用法：
 *   node tools/inspect-ai.js          # 打印前 40 步
 *   node tools/inspect-ai.js 120      # 打印前 120 步
 *
 * 和压测脚本的区别：压测看的是「结果」（达标率多少），
 * 这个脚本看的是「过程」（它每一步为什么这么走）。
 * 当初排查「达标率 0%、蛇只会撞墙」的 bug 靠的就是它 ——
 * 一打印就发现 AI 从头到尾没出现过「追击」这个决策，说明最短路径那条分支
 * 从来没命中过，顺着这条线索才查出距离场方向和障碍图两处问题。
 */

const path = require('path');
const core = require(path.join(__dirname, '..', 'game', 'snake-core.js'));

const STEPS = Number(process.argv[2] || 40);

const g = core.createGame();
console.log('棋盘 %d×%d | 初始蛇 %s | 食物 %s',
  core.COLS, core.ROWS, JSON.stringify(g.snake), JSON.stringify(g.food));
console.log('');

const tagCount = {};

for (let step = 1; step <= STEPS; step++) {
  const d = core.aiDecide(g);
  tagCount[d.tag] = (tagCount[d.tag] || 0) + 1;

  console.log('第 %s 步  [%s]  %s', String(g.steps + 1).padStart(3), d.tag, d.note);
  if (!d.dir) { console.log('  → AI 返回空方向，无路可走'); break; }

  const r = core.advance(g, d.dir);
  if (r !== 'ok') {
    console.log('  → 本局结束：%s（得分 %d，共 %d 步）', r, g.score, g.steps);
    break;
  }
}

console.log('');
console.log('决策类型统计：', JSON.stringify(tagCount));
console.log('说明：tag 含义 —— eat 吃食 / food 追击 / tail 追尾 / space 兜底 / dead 绝境');
console.log('正常运行时大部分步数应该是 food（追击），偶尔出现 tail（绕路等安全窗口）。');
