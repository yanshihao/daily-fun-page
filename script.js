const statusEl = document.querySelector('#status');
const cardsEl = document.querySelector('#cards');
const archiveEl = document.querySelector('#archiveList');
const todayTitle = document.querySelector('#todayTitle');
const template = document.querySelector('#cardTemplate');

function formatDate(dateText) {
  if (!dateText) return '今日精选';
  return `${dateText} 今日精选`;
}

function renderCards(items = []) {
  cardsEl.innerHTML = '';
  if (!items.length) {
    cardsEl.innerHTML = '<article class="card"><h3>今天还没有内容</h3><p class="summary">稍后再来看看，或者等待 GitHub Actions 自动更新。</p></article>';
    return;
  }

  for (const item of items) {
    const node = template.content.cloneNode(true);
    node.querySelector('.emoji').textContent = item.emoji || '✨';
    node.querySelector('.source').textContent = item.source || 'Daily Fun';
    node.querySelector('h3').textContent = item.title || '未命名趣味';
    node.querySelector('.summary').textContent = item.summary || '';
    const link = node.querySelector('.read-more');
    link.href = item.url || '#';
    cardsEl.appendChild(node);
  }
}

function renderArchive(archive = []) {
  archiveEl.innerHTML = '';
  if (!archive.length) {
    archiveEl.innerHTML = '<span>暂无往期归档</span>';
    return;
  }

  for (const entry of archive.slice(0, 14)) {
    const a = document.createElement('a');
    a.href = entry.path;
    a.textContent = entry.date;
    a.target = '_blank';
    a.rel = 'noreferrer';
    archiveEl.appendChild(a);
  }
}

async function loadDailyFun() {
  try {
    const response = await fetch(`data/today.json?ts=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    todayTitle.textContent = formatDate(data.date);
    statusEl.textContent = `已更新：${data.date || '今天'} · 共 ${data.items?.length || 0} 条趣味`;
    statusEl.classList.add('good');
    renderCards(data.items || []);
    renderArchive(data.archive || []);
  } catch (error) {
    console.error(error);
    statusEl.textContent = '读取失败：请稍后重试或检查 data/today.json';
    statusEl.classList.add('bad');
    renderCards([]);
    renderArchive([]);
  }
}

loadDailyFun();
