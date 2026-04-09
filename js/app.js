// ========== 상태 ==========
let selectedDate = null; // 'YYYY-MM-DD'
let calendarMonth = null; // Date 객체 (해당 월의 1일)
let manifest = { posts: [] };

// ========== 초기화 ==========
document.addEventListener('DOMContentLoaded', async () => {
  await loadManifest();
  initDate();
  bindEvents();
});

async function loadManifest() {
  try {
    const res = await fetch('posts/manifest.json?' + Date.now());
    manifest = await res.json();
  } catch (e) {
    manifest = { posts: [] };
  }
}

function initDate() {
  // 한국 시간 기준 오늘 날짜
  const now = new Date();
  const koreaTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const todayStr = formatDate(koreaTime);

  // 오늘 글이 있으면 오늘, 없으면 가장 최신 날짜
  const todayPosts = manifest.posts.filter(p => p.date === todayStr);
  if (todayPosts.length > 0) {
    setSelectedDate(todayStr);
  } else if (manifest.posts.length > 0) {
    // 가장 최신 날짜 찾기
    const dates = manifest.posts.map(p => p.date).sort().reverse();
    setSelectedDate(dates[0]);
  } else {
    setSelectedDate(todayStr);
  }
}

function bindEvents() {
  // 날짜 버튼
  document.getElementById('date-btn').addEventListener('click', openCalendar);

  // 달력 오버레이 클릭으로 닫기
  document.getElementById('calendar-overlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeCalendar();
  });

  // 달력 이전/다음
  document.getElementById('cal-prev').addEventListener('click', () => {
    calendarMonth.setMonth(calendarMonth.getMonth() - 1);
    renderCalendar();
  });
  document.getElementById('cal-next').addEventListener('click', () => {
    calendarMonth.setMonth(calendarMonth.getMonth() + 1);
    renderCalendar();
  });

  // 제목 클릭 → 메인으로
  document.getElementById('title-link').addEventListener('click', (e) => {
    e.preventDefault();
    showMainView();
  });

  // 이메일 복사
  document.getElementById('email-copy').addEventListener('click', copyEmail);

  // 뒤로가기 버튼
  document.getElementById('back-btn').addEventListener('click', showMainView);
}

// ========== 날짜 관련 ==========
function formatDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatDateDisplay(dateStr) {
  const [y, m, d] = dateStr.split('-');
  return `${y}년 ${parseInt(m)}월 ${parseInt(d)}일`;
}

function setSelectedDate(dateStr) {
  selectedDate = dateStr;
  document.getElementById('current-date').textContent = formatDateDisplay(dateStr);
  renderArticles();
}

// ========== 달력 ==========
function openCalendar() {
  const [y, m] = selectedDate.split('-').map(Number);
  calendarMonth = new Date(y, m - 1, 1);
  renderCalendar();
  document.getElementById('calendar-overlay').classList.remove('hidden');
}

function closeCalendar() {
  document.getElementById('calendar-overlay').classList.add('hidden');
}

function renderCalendar() {
  const year = calendarMonth.getFullYear();
  const month = calendarMonth.getMonth();

  document.getElementById('cal-title').textContent =
    `${year}년 ${month + 1}월`;

  const firstDay = new Date(year, month, 1).getDay();
  const lastDate = new Date(year, month + 1, 0).getDate();

  // 글이 있는 날짜 목록
  const monthStr = `${year}-${String(month + 1).padStart(2, '0')}`;
  const postDates = new Set(
    manifest.posts
      .filter(p => p.date.startsWith(monthStr))
      .map(p => parseInt(p.date.split('-')[2]))
  );

  // 한국 시간 오늘
  const now = new Date();
  const koreaTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const todayStr = formatDate(koreaTime);
  const [selY, selM, selD] = selectedDate.split('-').map(Number);

  const container = document.getElementById('cal-days');
  container.innerHTML = '';

  // 빈 칸
  for (let i = 0; i < firstDay; i++) {
    const el = document.createElement('div');
    el.className = 'cal-day empty';
    container.appendChild(el);
  }

  // 날짜
  for (let d = 1; d <= lastDate; d++) {
    const el = document.createElement('div');
    el.className = 'cal-day';
    el.textContent = d;

    const thisDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

    if (thisDateStr === todayStr) el.classList.add('today');
    if (year === selY && month === selM - 1 && d === selD) el.classList.add('selected');
    if (postDates.has(d)) el.classList.add('has-posts');

    el.addEventListener('click', () => {
      setSelectedDate(thisDateStr);
      closeCalendar();
      showMainView();
    });

    container.appendChild(el);
  }
}

// ========== 글 목록 렌더링 ==========
function renderArticles() {
  const categories = ['knowledge', 'news', 'daily'];
  categories.forEach(cat => {
    const listEl = document.querySelector(`.article-list[data-category="${cat}"]`);
    listEl.innerHTML = '';

    const posts = manifest.posts.filter(
      p => p.date === selectedDate && p.category === cat
    );

    if (posts.length === 0) {
      listEl.innerHTML = '<div class="no-articles">작성된 글이 없습니다.</div>';
      return;
    }

    posts.forEach(post => {
      const el = document.createElement('div');
      el.className = 'article-preview';
      el.addEventListener('click', () => openArticle(post));

      // 순수 텍스트 추출 (HTML 태그 제거)
      const plainText = stripHtml(post.preview || '');
      const escaped = escapeHtml(plainText);
      const firstChar = escaped.charAt(0);
      const rest = escaped.slice(1);

      el.innerHTML = `
        <div class="preview-title">${escapeHtml(post.title || '')}</div>
        <div class="preview-body">
          <div class="preview-text"><span class="preview-dropcap">${firstChar}</span>${rest}</div>
        </div>
      `;

      listEl.appendChild(el);
    });
  });
}

// ========== 글 상세보기 ==========
async function openArticle(post) {
  try {
    const res = await fetch(`posts/${post.file}?` + Date.now());
    const data = await res.json();

    document.getElementById('article-content').innerHTML = data.content;
    document.getElementById('main-content').classList.add('hidden');
    document.getElementById('article-view').classList.remove('hidden');
  } catch (e) {
    alert('글을 불러오는 데 실패했습니다.');
  }
}

function showMainView() {
  document.getElementById('article-view').classList.add('hidden');
  document.getElementById('main-content').classList.remove('hidden');
}

// ========== 이메일 복사 ==========
function copyEmail() {
  navigator.clipboard.writeText('roroyh47@gmail.com').then(() => {
    const toast = document.getElementById('copy-toast');
    toast.classList.remove('hidden');
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.classList.add('hidden'), 300);
    }, 1800);
  });
}

// ========== 유틸리티 ==========
function stripHtml(html) {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  return tmp.textContent || tmp.innerText || '';
}

function escapeHtml(str) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return str.replace(/[&<>"']/g, c => map[c]);
}
