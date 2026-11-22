# WAV Share

A small public WAV listening page. The browser plays files directly from the server; Express static serving supports HTTP range requests for seeking.


## Requirements
- Node.js 18+ recommended

## Run locally
```sh
npm install
UPLOAD_TOKEN='choose-a-long-secret' npm start
```
Open http://localhost:3000

Put WAV files in `public/audio/` to publish them. Or use the page's Upload WAV files panel and enter the upload token configured in `UPLOAD_TOKEN`.


## Deploy
Deploy this folder to a Node-capable host that supports persistent disk storage. Set the environment variable `UPLOAD_TOKEN` to a long, random value. Uploads are public to anyone who can access the page. The server currently stores uploaded files on disk; for hosts with ephemeral storage, use object storage or a persistent volume.


## Notes
- Only `.wav` uploads are accepted.
- Public playback; protected upload endpoint.
- The server limits uploads to 1 GB per file and 30 files per upload request.
- Add authentication or access controls if you want private listening.
