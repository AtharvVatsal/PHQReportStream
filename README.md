# IRBn ReportStream

A Streamlit-based dashboard and report generator for automating the extraction of structured data from daily WhatsApp status reports of IRBn/Bns. Paste one or more battalion messages, and get a consolidated, styled Excel report ready to download.

---

## 🚀 Features

* **Strict Template Parsing**: Accurate extraction when reports follow the exact numbered template.
* **Smart Fuzzy Parsing**: Keyword‑based mapping for semi‑structured or shuffled sections.
* **Legacy Regex Fallback**: Ensures maximum safety for non‑standard inputs.
* **AI QA Assist (optional)**: DistilBERT question‑answering layer to verify and fill missing fields.
* **Batch Paste Mode**: Split multiple reports by delimiters (`---`, `#####`, `===`).
* **Styled Excel Output**: Consolidated Daily Status Report with proper formatting, headers, and column widths.
* **Enhanced UI**: Custom CSS, branded header, sidebar expanders, logo support, and live DataFrame view.

---

## 📦 Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. **Set up a Python environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Add your logo** (optional)

   * Place your `logo.png` inside an `assets/` folder at the project root:

     ```
     your-repo/
     ├── app.py
     ├── assets/
     │   └── logo.png
     └── requirements.txt
     ```

---

## ▶️ Running Locally

```bash
streamlit run app.py
```

Then open the URL shown in your browser (e.g., `http://localhost:8501`).

---

## ⚙️ Usage

1. **Settings Sidebar**

   * **AI Assist**: Toggle DistilBERT QA overlay on/off.
   * **Batch Mode**: Enable splitting by delimiters for multiple reports.

2. **Input Form**

   * Paste one or more WhatsApp report texts.
   * Click **Extract & Add to Report**.
   * Success messages show how many reports were added.

3. **Live View & Download**

   * Expand the live DataFrame to review parsed entries.
   * Click **Download Styled Excel Report** to save the consolidated report.
   * Use **Reset Table for New Day** to clear session data.

---

## ☁️ Deployment

1. Push your changes to GitHub.
2. In [Streamlit Cloud](https://streamlit.io/cloud), link your repository.
3. Configure any secrets or environment variables if needed.
4. Deploy — it will automatically pull the `assets/` folder and dependencies.

---

## 🤝 Contributing

1. Fork this repository.
2. Create a feature branch: `git checkout -b feature/YourFeature`.
3. Commit your changes: `git commit -m "Add new feature"`.
4. Push to the branch: `git push origin feature/YourFeature`.
5. Submit a pull request.

---

## 📜 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">
  <small>© 2025 IRBn ReportStream • Built with ❤️ by the Himachal Pradesh Police Technical Team</small>
</div>
