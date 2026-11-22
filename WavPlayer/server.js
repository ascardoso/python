const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');


const app = express();
const PORT = process.env.PORT || 3000;
const UPLOAD_TOKEN = process.env.UPLOAD_TOKEN || '';
const AUDIO_DIR = path.join(__dirname, 'public', 'audio');
fs.mkdirSync(AUDIO_DIR, { recursive: true });

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, AUDIO_DIR),
  filename: (_req, file, cb) => {
    const original = path.basename(file.originalname).replace(/[^a-zA-Z0-9._ -]/g, '_');
    const unique = crypto.randomBytes(3).toString('hex');
    cb(null, `${Date.now()}-${unique}-${original}`);
  }
});
const upload = multer({
  storage,
  limits: { fileSize: 1024 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    if (/\.wav$/i.test(file.originalname) || file.mimetype === 'audio/wav' || file.mimetype === 'audio/x-wav') cb(null, true);
    else cb(new Error('Only WAV files are accepted.'));
  }
});


app.use(express.static(path.join(__dirname, 'public')));
app.use('/audio', express.static(AUDIO_DIR, { acceptRanges: true, maxAge: '1h' }));


app.get('/api/files', (_req, res) => {
  const files = fs.readdirSync(AUDIO_DIR, { withFileTypes: true })
    .filter(entry => entry.isFile() && /\.wav$/i.test(entry.name))
    .map(entry => {
      const full = path.join(AUDIO_DIR, entry.name);
      const stat = fs.statSync(full);
      return { name: entry.name, url: `/audio/${encodeURIComponent(entry.name)}`, size: stat.size, modified: stat.mtime.toISOString() };
    })
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
  res.json(files);
});

app.post('/api/upload', upload.array('wavFiles', 30), (req, res) => {
  if (!UPLOAD_TOKEN) {
    for (const file of req.files || []) fs.unlinkSync(file.path);
    return res.status(503).json({ error: 'Uploads are disabled. Set UPLOAD_TOKEN on the server first.' });
  }
  if (req.body.token !== UPLOAD_TOKEN) {
    for (const file of req.files || []) fs.unlinkSync(file.path);
    return res.status(401).json({ error: 'Incorrect upload token.' });
  }
  res.json({ uploaded: (req.files || []).map(file => file.filename) });
});


app.use((err, _req, res, _next) => {
  res.status(400).json({ error: err.message || 'Upload error' });
});


app.listen(PORT, () => console.log(`WAV Share listening on http://localhost:${PORT}`));
