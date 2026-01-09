# 🔬 Hierarchical RAG System - Judge Evaluation Guide

## 🎯 Quick Start for Judges

This system provides **AI-powered petroleum well data analysis** with automatic borehole prioritization (S2 > S1 > Main Hole).

---

## 📋 Prerequisites

✅ **Python 3.8+** (Check: `python --version`)  
✅ **pip** (Python package manager)  
✅ **Internet connection** (for first-time model download ~220MB)  

---

## 🚀 Setup Instructions (5 Minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure API Key (Optional but Recommended)
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```

**Without API key:** System will still retrieve and rank documents, but won't generate AI answers.

### Step 3: Index Well Data
```bash
# Option A: Use the web interface (Recommended)
python run_simple.py
# Then open http://localhost:5000 and upload well folders

# Option B: From the old database (if available)
python -c "from backend.setup_demo import *; setup_demo_database()"
```

---

## 💻 Usage for Judges

### Method 1: Command-Line Interface (CLI) - **RECOMMENDED FOR JUDGES**

#### Interactive Mode (Best for Testing):
```bash
python query_cli.py
```

This launches an interactive session where you can ask multiple questions:
```
❓ Your question: What is the TVD of Well 1?
[System shows borehole analysis and AI-generated answer]

❓ Your question: Show production data
[Another query...]

❓ Your question: exit
```

#### Single Query Mode:
```bash
# Ask a specific question
python query_cli.py --query "What is the TVD of Well 1?"

# Query only images
python query_cli.py --query "Show production data" --mode images_only

# Query only text
python query_cli.py --query "What is the well depth?" --mode text_only
```

### Method 2: Web Interface
```bash
# Start the web server
python run_simple.py

# Open browser to http://localhost:5000
```

---

## 🎯 Key Features to Evaluate

### 1. ✅ Borehole Priority System
The system **automatically prioritizes** data from boreholes:
- **S2 (Sidetrack 2)** = Highest priority
- **S1 (Sidetrack 1)** = Medium priority  
- **Main Hole** = Lowest priority

**Test it:**
```bash
python query_cli.py --query "What is the TVD of Well 1?"
```

You'll see:
```
📍 Borehole Analysis:
   S2 (Priority 3): 5 documents
   S1 (Priority 2): 3 documents
   Main Hole (Priority 1): 10 documents

✅ Using Highest Priority: S2
   Filtered from 18 to 5 documents
```

### 2. ✅ Image OCR Extraction
The system extracts text from images in PDFs using Tesseract OCR.

**Test it:**
```bash
python query_cli.py --query "Show production data" --mode images_only
```

### 3. ✅ Professional AI Responses
Gemini AI generates professional, well-cited answers with proper technical tone.

**Test it:**
```bash
python query_cli.py --query "What is the completion interval?"
```

### 4. ✅ Multi-Modal Search
Searches across text documents, Excel files, and image-extracted content.

---

## 📊 Example Queries for Testing

```bash
# Well specifications
python query_cli.py --query "What is the TVD of Well 1?"
python query_cli.py --query "What is the measured depth of Well 2?"

# Production data
python query_cli.py --query "Show production rates"
python query_cli.py --query "What are the reservoir properties?"

# Image-specific queries
python query_cli.py --query "Show well diagram" --mode images_only
python query_cli.py --query "Display completion schematic" --mode images_only

# Technical queries
python query_cli.py --query "What is the casing size?"
python query_cli.py --query "Describe the well completion"
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              User Query (CLI or Web UI)                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Embedding Model (BAAI/bge-base-en-v1.5)        │
│              ↓                                          │
│         Vector Database Search                          │
│              ↓                                          │
│    🔍 Borehole Priority Filter (S2 > S1 > Main)        │
│              ↓                                          │
│         Top-K Document Retrieval                        │
│              ↓                                          │
│    🤖 Gemini AI Answer Generation                      │
│              ↓                                          │
│         Professional Response                           │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Application_RAG/
├── query_cli.py              ← CLI interface for judges ⭐
├── run_simple.py             ← Web server
├── requirements.txt          ← Dependencies
├── backend/
│   ├── config.py            ← Configuration
│   ├── rag_system.py        ← Core RAG logic
│   ├── borehole_handler.py  ← Borehole priority system ⭐
│   ├── gemini_handler.py    ← AI response generation
│   ├── document_processor.py ← Document parsing
│   └── image_extractor.py   ← OCR extraction
├── frontend/
│   └── templates/
│       └── rag_ui.html      ← Web interface
└── wells_complete_db.pkl     ← Vector database
```

---

## 🔧 Troubleshooting

### Issue: "Database not found"
**Solution:** Index wells first:
```bash
python run_simple.py
# Upload wells via web interface at http://localhost:5000
```

### Issue: "Module not found"
**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "Tesseract not found"
**Solution:** Image OCR requires Tesseract:
- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt-get install tesseract-ocr`
- Mac: `brew install tesseract`

### Issue: No AI answers
**Solution:** Set Gemini API key in `.env` file:
```
GEMINI_API_KEY=your_key_here
```

---

## 📈 Performance Metrics

- **Document Indexing:** ~500-1000 chunks per well
- **Query Speed:** <2 seconds for search + AI generation
- **Embedding Model:** 768-dimensional vectors
- **Borehole Filtering:** Automatic, zero configuration
- **Image OCR:** Supports PNG, JPG, PDF embedded images

---

## 🎓 Technical Highlights

1. **Hierarchical Vector Database:** Well → Document → Chunk structure
2. **Advanced Embeddings:** BAAI/bge-base-en-v1.5 (state-of-the-art)
3. **Smart Borehole Priority:** Automatic S2 > S1 > Main detection and filtering
4. **Multi-Modal:** Text + Image OCR extraction
5. **Professional AI:** Corporate-tone technical responses
6. **Production-Ready:** Error handling, logging, validation

---

## 📞 Support

For issues during evaluation:
1. Check `troubleshooting` section above
2. Review console output for error messages
3. Verify all dependencies are installed: `pip list`

---

## ✅ Evaluation Checklist

- [ ] Dependencies installed successfully
- [ ] Wells indexed (database exists)
- [ ] CLI runs without errors
- [ ] Can query via CLI and get responses
- [ ] Borehole priority filtering works (check console output)
- [ ] Image-only queries return results
- [ ] AI generates professional, cited answers
- [ ] Web UI accessible (optional)

---

**Thank you for evaluating our Hierarchical RAG System!** 🚀
