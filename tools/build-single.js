/**
 * 构建「单文件版」贪吃蛇：把逻辑层 snake-core.js 内联进 index.html，
 * 生成一份零外部引用、双击 file:// 即可打开的 game/snake-standalone.html。
 *
 * 为什么要有这一步：
 *   任务书作品要求写的是「纯前端单文件（HTML/CSS/JS），浏览器双击即可打开，无框架依赖」。
 *   开发时我们把逻辑（snake-core.js）和界面（index.html）拆成两层，是为了同一份 AI 算法
 *   能被 Node 直接 require 去做 300 局压测（见 tools/stress-test.js）。
 *   但拆开就成了「两个文件」，和「单文件」字面要求差一点。
 *   解法：源码保持两层（可测试），再自动生成一个内联的单文件交付版。
 *   两者逻辑同源，不会走样；单文件版专门用于「双击即开 / 满足单文件验收」。
 *
 * 用法：node tools/build-single.js
 */
const fs = require('fs');
const path = require('path');

const GAME_DIR = path.join(__dirname, '..', 'game');
const htmlPath = path.join(GAME_DIR, 'index.html');
const corePath = path.join(GAME_DIR, 'snake-core.js');
const outPath = path.join(GAME_DIR, 'snake-standalone.html');

const html = fs.readFileSync(htmlPath, 'utf8');
const core = fs.readFileSync(corePath, 'utf8');

// 安全检查：核心文件里不能出现 </script>，否则内联会断。
if (/<\/script/i.test(core)) {
  console.error('✗ 安全校验失败：snake-core.js 中含 </script>，无法安全内联。');
  process.exit(1);
}

const SRC_TAG = '<script src="snake-core.js"></script>';
if (!html.includes(SRC_TAG)) {
  console.error('✗ 在 index.html 中找不到 ' + SRC_TAG + '，可能结构已变。');
  process.exit(1);
}

const banner =
  '<!-- ============================================================\n' +
  '     单文件交付版（由 tools/build-single.js 自动生成）\n' +
  '     逻辑源：game/snake-core.js + game/index.html\n' +
'     不要直接编辑本文件！改源文件后重跑 `node tools/build-single.js`。\n' +
'     ============================================================ -->\n';

// 用函数式替换，避免 core 里的 $& 之类被当作替换占位符
const inlined = html.replace(
  SRC_TAG,
  banner + '<script>\n/* ===== snake-core.js 内联开始（自动生成，请勿手改） ===== */\n' +
    core + '\n/* ===== snake-core.js 内联结束 ===== */\n</script>'
);

if (inlined.includes('src="snake-core.js"')) {
  console.error('✗ 内联后仍存在外部引用 src="snake-core.js"。');
  process.exit(1);
}

fs.writeFileSync(outPath, inlined, 'utf8');
console.log('✓ 已生成 ' + path.relative(process.cwd(), outPath));
console.log('  大小: ' + (fs.statSync(outPath).size / 1024).toFixed(1) + ' KB');
console.log('  外部引用(src=)残留: ' + (inlined.match(/src=["']/g) || []).length + ' 个');
