const statusEl = document.querySelector('#status');
const cardsEl = document.querySelector('#cards');
const archiveEl = document.querySelector('#archiveList');
const todayTitle = document.querySelector('#todayTitle');
const template = document.querySelector('#cardTemplate');

let currentData = null;

function formatDate(dateText, versionId) {
  if (!dateText) return '今日精选';
  if (versionId && versionId.length > 11) {
    const timeText = versionId.slice(11).replaceAll('-', ':');
    return `${dateText} ${timeText} 精选`;
  }
  return `${dateText} 今日精选`;
}

function setStatus(text, type = '') {
  statusEl.classList.remove('good', 'bad');
  if (type) statusEl.classList.add(type);
  statusEl.textContent = text;
}

function renderCards(items = []) {
  cardsEl.innerHTML = '';
  if (!items.length) {
    cardsEl.innerHTML = '<article class="card"><h3>这一版还没有内容</h3><p class="summary">稍后再来看看，或者等待 GitHub Actions 自动更新。</p></article>';
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

function renderArchive(archive = [], activePath = 'data/today.json') {
  archiveEl.innerHTML = '';
  if (!archive.length) {
    archiveEl.innerHTML = '<span>暂无往期归档</span>';
    return;
  }

  for (const entry of archive.slice(0, 30)) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'archive-button';
    button.textContent = entry.date;
    button.dataset.path = entry.path;
    if (entry.path === activePath) button.classList.add('active');
    button.addEventListener('click', () => loadDailyFun(entry.path, false));
    archiveEl.appendChild(button);
  }
}

function renderDataset(data, path = 'data/today.json') {
  currentData = data;
  todayTitle.textContent = formatDate(data.date, data.version_id);
  const versionText = data.version_id ? ` · 版本 ${data.version_id.slice(11).replaceAll('-', ':')}` : '';
  setStatus(`已加载：${data.date || '今天'}${versionText} · 共 ${data.items?.length || 0} 条趣味`, 'good');
  renderCards(data.items || []);
  renderArchive(data.archive || [], path);
}

async function loadDailyFun(path = 'data/today.json', cacheBust = true) {
  try {
    setStatus('正在读取内容……');
    const separator = path.includes('?') ? '&' : '?';
    const url = cacheBust ? `${path}${separator}ts=${Date.now()}` : path;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderDataset(data, path);

    // Keep the selected version in the URL without leaving the page.
    const pageUrl = new URL(window.location.href);
    if (path === 'data/today.json') {
      pageUrl.searchParams.delete('version');
    } else {
      pageUrl.searchParams.set('version', path);
    }
    window.history.replaceState({}, '', pageUrl);
  } catch (error) {
    console.error(error);
    setStatus('读取失败：请稍后重试或检查数据文件', 'bad');
    if (!currentData) {
      renderCards([]);
      renderArchive([]);
    }
  }
}

function init() {
  const params = new URLSearchParams(window.location.search);
  const versionPath = params.get('version');
  if (versionPath && versionPath.startsWith('data/') && versionPath.endsWith('.json')) {
    loadDailyFun(versionPath, true);
  } else {
    loadDailyFun();
  }
}

init();
