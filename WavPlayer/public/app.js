const audio = document.getElementById('audio');
const list = document.getElementById('list');
const search = document.getElementById('search');
const currentTitle = document.getElementById('currentTitle');
const meta = document.getElementById('meta');
const count = document.getElementById('count');
const empty = document.getElementById('empty');
let files = [];
let currentUrl = '';

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function render() {
  const term = search.value.trim().toLowerCase();
  const filtered = files.filter(file => file.name.toLowerCase().includes(term));
  list.innerHTML = '';
  count.textContent = `${files.length} ${files.length === 1 ? 'track' : 'tracks'}`;
  empty.hidden = filtered.length > 0;
  if (files.length === 0) empty.textContent = "No WAV files found. Add files to the server's public/audio folder.";
  else if (!filtered.length) empty.textContent = 'No files match your search.';
  filtered.forEach(file => {
    const row = document.createElement('div');
    row.className = `track${file.url === currentUrl ? ' active' : ''}`;
    row.tabIndex = 0;
    row.setAttribute('role', 'button');
    row.innerHTML = `<div class="track-icon">♫</div><div class="track-name"></div><div class="track-size">${formatSize(file.size)}</div><div class="track-play">▶</div>`;
    row.querySelector('.track-name').textContent = file.name;
    const activate = () => playFile(file);
    row.addEventListener('click', activate);
    row.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); } });
    list.appendChild(row);
  });
}
function playFile(file) {
  currentUrl = file.url;
  audio.src = file.url;
  currentTitle.textContent = file.name;
  meta.textContent = `${formatSize(file.size)} · WAV audio`;
  audio.play().catch(() => { meta.textContent = `${formatSize(file.size)} · Press play to begin`; });
  render();
}
async function loadLibrary() {
  try {
    const res = await fetch('/api/files');
    if (!res.ok) throw new Error('Library could not be loaded');
    files = await res.json();
    render();
  } catch (err) {
    empty.hidden = false;
    empty.textContent = err.message;
  }
}
search.addEventListener('input', render);
document.getElementById('refresh').addEventListener('click', loadLibrary);
document.getElementById('uploadForm').addEventListener('submit', async event => {
  event.preventDefault();
  const fileInput = document.getElementById('fileInput');
  const token = document.getElementById('token').value;
  const status = document.getElementById('uploadStatus');
  if (!fileInput.files.length) { status.textContent = 'Choose at least one WAV file first.'; return; }
  const form = new FormData();
  for (const file of fileInput.files) form.append('wavFiles', file);
  form.append('token', token);
  status.textContent = 'Uploading…';
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Upload failed');
    status.textContent = `Uploaded ${data.uploaded.length} file(s).`;
    fileInput.value = '';
    await loadLibrary();
  } catch (err) { status.textContent = err.message; }
});
audio.addEventListener('ended', () => {
  const index = files.findIndex(file => file.url === currentUrl);
  if (index >= 0 && index + 1 < files.length) playFile(files[index + 1]);
});
loadLibrary();
