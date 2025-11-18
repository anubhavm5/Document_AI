# Document AI for Invoice Information Extraction  
### Using Donut Model + Google Gemini API

This project automates the extraction of key information from invoice documents using a combination of **Donut (Document Understanding Transformer)** and the **Google Gemini API**.  
It converts unstructured invoice PDFs/images into structured JSON output — reducing manual data entry and improving accuracy.

---

## 🚀 Features

- Extracts essential invoice details:
  - Vendor Name  
  - Buyer Name  
  - Invoice Number  
  - Invoice Date  
  - Total Amount  
  - Line Items (if available)
- Supports **PDF**, **JPEG**, and **PNG** formats  
- Hybrid extraction pipeline using:
  - **Donut** for vision-based document understanding  
  - **Gemini API** for refined text extraction & validation  
- Outputs clean, structured **JSON**  
- Modular & extendable pipeline  

---

## 🧠 Tech Stack

| Component | Technology |
|----------|------------|
| Document Understanding | Donut (HuggingFace) |
| LLM Processing | Google Gemini API |
| Programming Language | Python |
| Data Handling | JSON, Pydantic |
| Preprocessing | OpenCV, PIL |

---

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/DocumentAI-Invoice-Extraction.git
cd DocumentAI-Invoice-Extraction
