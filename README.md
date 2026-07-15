# StockMind - Replenishment AI Planner

StockMind is an autonomous AI-driven inventory replenishment planner that uses a multi-agent LangGraph architecture, vector policies (RAG), and a FastAPI + Streamlit tech stack to calculate optimal orders.

---

## 🛠️ Step-by-Step Local Setup

Follow these steps to run the application on your computer:

### 1. Prerequisites
Ensure you have Python (version 3.10 or higher) installed. Open your terminal (PowerShell, Command Prompt, or bash) in the project directory:
```bash
c:\Users\ameen\OneDrive\Dokumen\inventory\inventory-planner
```

### 2. Install Dependencies
Run the following command to install all required libraries (including FastAPI, Streamlit, LangGraph, and embedding utilities):
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Open the `.env` file in the root directory and add your Google Gemini API key:
```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here
```
*(If you do not have an active Gemini API key, the system will automatically use intelligent safety-stock fallback rules to generate realistic replenishment reasons and values, preventing crashes).*

### 4. Seed the Database
Initialize and seed the local SQLite database (`data/inventory.db`) with real product list records and sales history:
```bash
python scripts/seed_database.py
```

---

## 🚀 Running the Application

To launch both the FastAPI backend and the Streamlit frontend UI simultaneously, simply run the unified launcher script:

```bash
python run_app.py
```

* **What this does**: 
  * Automatically frees up ports `8000` (Backend) and `8501` (Frontend) if they are currently in use.
  * Launches the FastAPI backend on [http://127.0.0.1:8000](http://127.0.0.1:8000) and the Streamlit frontend.
  * Forwards real-time logs from both services to your terminal.
  * Gracefully shuts down both processes when you press `CTRL+C`.
* **Accessing the Dashboard**: Open [http://localhost:8501](http://localhost:8501) in your web browser.

---

## ⚙️ How to Test and Interact

- **Overview Page**: View real-time KPI metrics, critical low-stock alerts, and category velocity trends.
- **Inventory & Suppliers**: Review stock statuses (Critical, Low, Healthy) and vendor performance.
- **AI Agent Page**: 
  - Click **"Trigger AI Replenishment"** in the sidebar or click **"Yes"** on a restock alert to automatically run the agent pipeline.
  - Review actionable replenishment orders, the RAG policy context logs, the AI Executive report, and the step-by-step LangGraph node trace logs.
  - Approve or reject proposed orders directly from the UI.