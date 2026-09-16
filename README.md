# Python Scripts
Helpful scripts in Python (made via chatGPT) <br>
Working on macOS 26.6.2, Python 3.13.14

Make sure requirements are fulfilled 
<p>pip install -r /path/to/requirements.txt

<b>WebViewerEditor.py</b> reads a bookmark.html file, de-dupes entries. Selecting one will display its contents. Allows for check validation (404) and removal of those sites, plus using a Json-file to save state (working site or not)

<b>FileViewer.py</b> Asks for a folder to be opened/selected, then lists all files on its left pane, selecting one will display its contents. Editing, search and sorting enabled. Supports .txt, .rtf, .rtfd, .png, .jpg and other text and image files

<b>ExportMessages.py</b> is a macOS utility that reads the local Apple Messages `chat.db` database and exports conversations to human-readable text files. It can identify contacts/conversations, recover message text (including `NSAttributedString` content via `pytypedstream`), preserve dates and sender names, and export associated attachments when their local files can be resolved. </p>Run with --all or a given contact.

<b>Spectrogram.py</b> Loads a WAV recording and analyzes its audio spectrum to find the fundamental frequency (F₀) and harmonics.
And displays a large spectrogram, FFT spectrum, and numbered harmonic frequencies for visual analysis.   

***  To run these scripts from terminal place them in a folder that is in PATH and run 'chmod +x <script>'
