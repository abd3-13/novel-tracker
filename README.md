# Novel Tracker 📚

A web application to track your novels — supports local EPUB metadata extraction and online tracking via Webnovel API, with chapter count tracking, cover management, and reading progress. Built with Python + Flask, SQLite, and a JS-powered table (DataTables) front-end.

## Features

- Track novels with **local EPUB** metadata (title, author, description, cover)  
- Automatically fetch **online chapter counts** from Webnovel (and potentially other sources)  
- Store and display **local and online chapter progress**  
- Support for **cover images**, stored locally or fetched online  
- Clean UI using DataTables + jQuery for sorting/searching/filtering novels  
- Simple, self-contained backend using Flask + SQLite — no heavy dependencies  
- Easy to run locally or deploy on a server  

## 📦 Installation & Setup

1. Clone the repo  
   ```bash
   git clone https://github.com/abd3-13/novel-tracker.git
   cd novel-tracker
   ```

2. (Optional but recommended) Create a virtual environment and activate it  
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```

3. Install dependencies  
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables  
   - Copy `.env.example` to `.env`  
   - Edit `.env` to set:  
     - `LOCAL_EPUB_DIR` → path where your EPUB files are stored  
     - (Optional) `SECRET_KEY`, other configs  

5. Initialize database  
   - If not already created, run a script or use the app’s built-in initialization (depends on your setup)  
   - Ensure `instance/` folder exists and is writable  

6. Run the app  
   ```bash
   flask --app app run
   ```  
   Then open `http://127.0.0.1:5000` in your browser

## 🧰 How to Use

- **Add a novel**  
  Use the “Add Novel” form — supply a name and either a URL (for online source) or upload/or specify an EPUB file path for local metadata.

- **View and manage novels**  
  The main table displays all novels. Columns include local vs online chapters, difference, status, notes, etc. You can sort/search/filter easily.

- **Update metadata / progress**  
  The “Update” action will:  
  - Fetch the latest online chapter count (if source is online)  
  - Extract local metadata (if EPUB exists) — such as author, description, cover  

- **Cover images**  
  Cover images from EPUB or online sources are saved under `static/img/cover/` (or your configured cover folder).  

## 📁 Project Structure (simplified)

```
novel-tracker/
├── app.py             # application entrypoint
├── config.py          # configuration and env loading
├── utils/             # helper modules (db, epub extraction, webnovel API, etc.)
├── routes/            # app routes / endpoints
├── templates/         # HTML templates (with DataTables + jQuery)
├── static/            # CSS / JS / cover images
├── requirements.txt   # dependencies
├── .env.example       # example env configuration
└── .gitignore         # files/folders to ignore in version control
```
Some changes are coming to structures

## 🔐 Licenses & Third-Party Libraries

- This project is licensed under the **MIT License**.  
- Third-party libraries used:  
  - [jQuery](https://jquery.com) — MIT License  
  - [DataTables](https://datatables.net) — MIT License  
  - Other Python dependencies (see `requirements.txt`)  

Please refer to the `LICENSE` and `LICENSES.md` files for full license texts.

## 💡 Why I Built This

I wanted a small, manageable tool to track my reading progress, both for local EPUBs and online-hosted novels — with minimal setup and full control. I turned that into a simple, flexible web app so I (and others) can reuse it for personal novel tracking.

## 🛠️ Future / TODO Ideas

- Add support for more online novel platforms beyond Webnovel  
- Improve EPUB metadata extraction (cover images, language, tags)  
- Add user-auth / multi-user support  
- Add remote deployment instructions (Docker, cloud, etc.)  
- Add export/import (e.g. CSV, JSON) for backup/sharing  

---

