#!/usr/bin/env python3
"""
로로 紙 - 글 작성 에디터
실행: python editor.py
브라우저에서 http://localhost:8080 접속
"""

import http.server
import json
import os
import subprocess
import urllib.parse
import datetime
import socketserver

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, 'posts')

CATEGORY_MAP = {
    'knowledge': '지식 한 조각',
    'news': '요즘 소식',
    'daily': '연호의 하루'
}

EDITOR_HTML = r'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>로로 紙 - 글 작성</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif; background: #f5f5f0; }

    .header {
      background: #fff;
      border-bottom: 1px solid #ddd;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .header h1 { font-size: 20px; }
    .header-actions { display: flex; gap: 8px; }

    .meta-bar {
      background: #fff;
      padding: 12px 24px;
      border-bottom: 1px solid #eee;
      display: flex;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
    }
    .meta-bar label { font-size: 14px; font-weight: 600; }
    .meta-bar input, .meta-bar select {
      padding: 6px 10px;
      border: 1px solid #ccc;
      border-radius: 6px;
      font-size: 14px;
    }

    .toolbar {
      background: #fff;
      padding: 8px 24px;
      border-bottom: 1px solid #eee;
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
      align-items: center;
    }
    .toolbar button, .toolbar select, .toolbar input {
      padding: 5px 10px;
      border: 1px solid #ccc;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 13px;
    }
    .toolbar button:hover { background: #f0f0f0; }
    .toolbar button.active { background: #e0e7ff; border-color: #818cf8; }
    .toolbar .sep { width: 1px; height: 24px; background: #ddd; margin: 0 4px; }
    .toolbar input[type="color"] { width: 32px; height: 28px; padding: 2px; }

    #editor {
      max-width: 760px;
      margin: 24px auto;
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      min-height: 500px;
      padding: 24px;
      font-size: 16px;
      line-height: 1.8;
      outline: none;
      overflow-y: auto;
    }

    .btn-primary {
      background: #2563eb;
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 8px 20px;
      font-size: 14px;
      cursor: pointer;
      font-weight: 600;
    }
    .btn-primary:hover { background: #1d4ed8; }

    .btn-secondary {
      background: #fff;
      color: #333;
      border: 1px solid #ccc;
      border-radius: 6px;
      padding: 8px 16px;
      font-size: 14px;
      cursor: pointer;
    }
    .btn-secondary:hover { background: #f0f0f0; }

    .toast {
      position: fixed;
      bottom: 30px;
      left: 50%;
      transform: translateX(-50%);
      background: #333;
      color: #fff;
      padding: 12px 28px;
      border-radius: 8px;
      font-size: 14px;
      z-index: 999;
      display: none;
    }
    .toast.show { display: block; }

    /* 기존 글 목록 */
    .post-list {
      max-width: 760px;
      margin: 20px auto;
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 16px;
    }
    .post-list h3 { margin-bottom: 12px; font-size: 16px; }
    .post-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid #eee;
    }
    .post-item:last-child { border-bottom: none; }
    .post-item-info { font-size: 14px; }
    .post-item-info .cat { color: #888; font-size: 12px; }
    .post-item-actions { display: flex; gap: 6px; }
    .btn-sm {
      padding: 4px 10px;
      font-size: 12px;
      border: 1px solid #ccc;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
    }
    .btn-sm:hover { background: #f0f0f0; }
    .btn-sm.danger { color: #dc2626; border-color: #fca5a5; }
    .btn-sm.danger:hover { background: #fef2f2; }
  </style>
</head>
<body>
  <div class="header">
    <h1>로로 紙 - 글 작성</h1>
    <div class="header-actions">
      <button class="btn-secondary" onclick="loadPostList()">글 목록 새로고침</button>
    </div>
  </div>

  <div class="meta-bar">
    <div>
      <label>날짜:</label>
      <input type="date" id="post-date">
    </div>
    <div>
      <label>카테고리:</label>
      <select id="post-category">
        <option value="knowledge">지식 한 조각</option>
        <option value="news">요즘 소식</option>
        <option value="daily">연호의 하루</option>
      </select>
    </div>
    <div>
      <label>제목:</label>
      <input type="text" id="post-title" placeholder="글 제목" style="width: 250px;">
    </div>
  </div>

  <div class="toolbar">
    <button onclick="execCmd('bold')" title="굵게"><b>B</b></button>
    <button onclick="execCmd('italic')" title="기울임"><i>I</i></button>
    <button onclick="execCmd('underline')" title="밑줄"><u>U</u></button>
    <div class="sep"></div>
    <select onchange="execFontSize(this.value); this.value='';">
      <option value="">글씨 크기</option>
      <option value="1">매우 작게</option>
      <option value="2">작게</option>
      <option value="3">보통</option>
      <option value="4">조금 크게</option>
      <option value="5">크게</option>
      <option value="6">매우 크게</option>
      <option value="7">최대</option>
    </select>
    <div class="sep"></div>
    <label title="글씨 색상" style="display:flex;align-items:center;gap:4px;font-size:13px;cursor:pointer;">
      색상: <input type="color" id="text-color" value="#000000" onchange="execCmd('foreColor', this.value)">
    </label>
    <div class="sep"></div>
    <button onclick="execCmd('justifyLeft')" title="왼쪽 정렬">⫷</button>
    <button onclick="execCmd('justifyCenter')" title="가운데 정렬">⫿</button>
    <div class="sep"></div>
    <button class="btn-primary" onclick="savePost()" style="margin-left: auto;">저장 & 배포</button>
  </div>

  <div id="editor" contenteditable="true">
    <p>여기에 글을 작성하세요...</p>
  </div>

  <div class="post-list" id="post-list-section">
    <h3>기존 글 목록</h3>
    <div id="post-list"></div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    let editingFile = null; // 수정 중인 파일명

    // 오늘 날짜 기본값
    const today = new Date();
    const koreaOffset = 9 * 60;
    const utcMs = today.getTime() + today.getTimezoneOffset() * 60000;
    const koreaDate = new Date(utcMs + koreaOffset * 60000);
    document.getElementById('post-date').value =
      koreaDate.getFullYear() + '-' +
      String(koreaDate.getMonth() + 1).padStart(2, '0') + '-' +
      String(koreaDate.getDate()).padStart(2, '0');

    function execCmd(cmd, val) {
      document.execCommand(cmd, false, val || null);
      document.getElementById('editor').focus();
    }

    function execFontSize(size) {
      if (size) {
        document.execCommand('fontSize', false, size);
        document.getElementById('editor').focus();
      }
    }

    function showToast(msg, duration) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), duration || 2500);
    }

    async function savePost() {
      const date = document.getElementById('post-date').value;
      const category = document.getElementById('post-category').value;
      const title = document.getElementById('post-title').value.trim();
      const content = document.getElementById('editor').innerHTML;

      if (!date) { alert('날짜를 선택하세요.'); return; }
      if (!title) { alert('제목을 입력하세요.'); return; }
      if (!content || content === '<p>여기에 글을 작성하세요...</p>') {
        alert('글 내용을 입력하세요.'); return;
      }

      const body = { date, category, title, content };
      if (editingFile) body.editFile = editingFile;

      try {
        const res = await fetch('/api/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        const result = await res.json();
        if (result.success) {
          showToast('저장 및 배포 완료!');
          editingFile = null;
          document.getElementById('editor').innerHTML = '<p>여기에 글을 작성하세요...</p>';
          document.getElementById('post-title').value = '';
          loadPostList();
        } else {
          alert('오류: ' + result.error);
        }
      } catch (e) {
        alert('저장 실패: ' + e.message);
      }
    }

    async function loadPostList() {
      try {
        const res = await fetch('/api/posts');
        const data = await res.json();
        const list = document.getElementById('post-list');
        if (data.posts.length === 0) {
          list.innerHTML = '<div style="color:#aaa;padding:12px;">아직 글이 없습니다.</div>';
          return;
        }
        const catNames = { knowledge: '지식 한 조각', news: '요즘 소식', daily: '연호의 하루' };
        list.innerHTML = data.posts.map(p => `
          <div class="post-item">
            <div class="post-item-info">
              <strong>${p.title}</strong>
              <span class="cat">[${catNames[p.category] || p.category}]</span>
              <span class="cat">${p.date}</span>
            </div>
            <div class="post-item-actions">
              <button class="btn-sm" onclick="editPost('${p.file}')">수정</button>
              <button class="btn-sm danger" onclick="deletePost('${p.file}')">삭제</button>
            </div>
          </div>
        `).join('');
      } catch (e) {
        console.error(e);
      }
    }

    async function editPost(file) {
      try {
        const res = await fetch('/api/post?file=' + encodeURIComponent(file));
        const data = await res.json();
        document.getElementById('post-date').value = data.date;
        document.getElementById('post-category').value = data.category;
        document.getElementById('post-title').value = data.title;
        document.getElementById('editor').innerHTML = data.content;
        editingFile = file;
        window.scrollTo(0, 0);
        showToast('글을 불러왔습니다. 수정 후 "저장 & 배포"를 클릭하세요.');
      } catch (e) {
        alert('글 불러오기 실패');
      }
    }

    async function deletePost(file) {
      if (!confirm('정말 삭제하시겠습니까?')) return;
      try {
        const res = await fetch('/api/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file })
        });
        const result = await res.json();
        if (result.success) {
          showToast('삭제 및 배포 완료!');
          loadPostList();
        } else {
          alert('오류: ' + result.error);
        }
      } catch (e) {
        alert('삭제 실패');
      }
    }

    // 초기 로드
    loadPostList();

    // 에디터 포커스 시 기본 텍스트 제거
    document.getElementById('editor').addEventListener('focus', function() {
      if (this.innerHTML === '<p>여기에 글을 작성하세요...</p>') {
        this.innerHTML = '';
      }
    });
  </script>
</body>
</html>
'''


class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == '/editor':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(EDITOR_HTML.encode('utf-8'))
            return

        if parsed.path == '/api/posts':
            self.send_json(load_manifest())
            return

        if parsed.path == '/api/post':
            qs = urllib.parse.parse_qs(parsed.query)
            filename = qs.get('file', [None])[0]
            if filename:
                filepath = os.path.join(POSTS_DIR, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.send_json(data)
                    return
            self.send_json({'error': 'not found'}, 404)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == '/api/save':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            result = save_post(body)
            self.send_json(result)
            return

        if parsed.path == '/api/delete':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            result = delete_post(body.get('file'))
            self.send_json(result)
            return

        self.send_json({'error': 'not found'}, 404)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        # 간소화된 로그
        pass


def load_manifest():
    manifest_path = os.path.join(POSTS_DIR, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'posts': []}


def save_manifest(data):
    manifest_path = os.path.join(POSTS_DIR, 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_preview(html_content):
    """HTML에서 텍스트만 추출하여 미리보기 생성"""
    import re
    text = re.sub(r'<[^>]+>', '', html_content)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = ' '.join(text.split())
    return text[:200]


def save_post(body):
    try:
        date = body['date']
        category = body['category']
        title = body['title']
        content = body['content']
        edit_file = body.get('editFile')

        manifest = load_manifest()

        if edit_file:
            # 수정: 기존 파일 삭제
            manifest['posts'] = [p for p in manifest['posts'] if p['file'] != edit_file]
            old_path = os.path.join(POSTS_DIR, edit_file)
            if os.path.exists(old_path):
                os.remove(old_path)

        # 파일명 생성
        timestamp = datetime.datetime.now().strftime('%H%M%S')
        filename = f"{date}_{category}_{timestamp}.json"

        # 글 저장
        post_data = {
            'date': date,
            'category': category,
            'title': title,
            'content': content
        }

        filepath = os.path.join(POSTS_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, ensure_ascii=False, indent=2)

        # 미리보기 텍스트 추출
        preview = extract_preview(content)

        # manifest 업데이트
        manifest['posts'].append({
            'file': filename,
            'date': date,
            'category': category,
            'title': title,
            'preview': preview
        })

        # 날짜 역순 정렬
        manifest['posts'].sort(key=lambda x: x['date'], reverse=True)
        save_manifest(manifest)

        # Git 커밋 & 푸시
        deploy()

        return {'success': True, 'file': filename}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def delete_post(filename):
    try:
        if not filename:
            return {'success': False, 'error': 'No file specified'}

        manifest = load_manifest()
        manifest['posts'] = [p for p in manifest['posts'] if p['file'] != filename]
        save_manifest(manifest)

        filepath = os.path.join(POSTS_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

        deploy()

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def deploy():
    """Git add, commit, push"""
    try:
        subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR, check=True,
                       capture_output=True, text=True)
        subprocess.run(
            ['git', 'commit', '-m', f'글 업데이트 - {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'],
            cwd=BASE_DIR, check=True, capture_output=True, text=True
        )
        subprocess.run(['git', 'push'], cwd=BASE_DIR, check=True,
                       capture_output=True, text=True)
        print('[배포] Git push 완료')
    except subprocess.CalledProcessError as e:
        print(f'[배포 경고] {e.stderr or e.stdout or str(e)}')


if __name__ == '__main__':
    # 에디터 페이지 자동 열기
    import webbrowser
    import threading

    print(f'로로 紙 에디터 서버 시작: http://localhost:{PORT}/editor')
    print('종료하려면 Ctrl+C를 누르세요.')

    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{PORT}/editor')).start()

    with socketserver.TCPServer(('', PORT), EditorHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n서버 종료.')
