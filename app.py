import streamlit as st
from PIL import Image
import pandas as pd
import io
import os
import json

from donut_utils import load_donut, extract_with_donut
from gemini_extractor import extract_invoice_universal

st.set_page_config(page_title="DOCAI", layout="wide")
st.title("DOCUMENT AI")

st.write("""
Smart Invoice Information Extraction Using Donut + Gemini AI
""")

uploaded_files = st.file_uploader(
    "📤 Upload one or more invoices (images or PDFs)",
    accept_multiple_files=True,
    type=["png", "jpg", "jpeg", "pdf"]
)

# Load Donut once
processor, model, device = load_donut()

if uploaded_files:
    os.makedirs("outputs", exist_ok=True)
    all_rows = []
    summaries = []

    for f in uploaded_files:
        st.divider()
        st.write(f"**Processing File:** {f.name}")

        temp_path = os.path.join("outputs", f.name)
        with open(temp_path, "wb") as out_f:
            out_f.write(f.getbuffer())

        # Step 1: Donut extraction
        try:
            if f.name.lower().endswith(".pdf"):
                from pdf2image import convert_from_path
                pages = convert_from_path(temp_path, dpi=300)
                pil_img = pages[0]
            else:
                pil_img = Image.open(temp_path).convert("RGB")

            with st.spinner("🔍 Running Donut model..."):
                donut_result = extract_with_donut(pil_img, processor, model, device)
                donut_struct = donut_result.get("structured_data", {})
                st.success("✅ Donut extraction complete")
        except Exception as e:
            st.error(f"❌ Donut failed: {e}")
            donut_struct = {"error": str(e)}

        # Step 2: Gemini refinement
        try:
            with st.spinner("💡 Refining with Gemini AI..."):
                gemini_result = extract_invoice_universal(temp_path)
                gemini_struct = gemini_result.get("structured_data", {})
                gemini_summary = gemini_result.get("summary", "")
                st.success("✅ Gemini refinement complete")
        except Exception as e:
            st.error(f"❌ Gemini failed: {e}")
            gemini_struct = {"error": str(e)}
            gemini_summary = ""

        # Combine results
        final_struct = gemini_struct if gemini_struct and not gemini_struct.get("error") else donut_struct

        # Clean up amounts (fix commas/dots)
        for key in ["subtotal", "tax", "grand_total"]:
            if key in final_struct and isinstance(final_struct[key], str):
                value = final_struct[key].replace(",", ".").strip()
                # Ensure $ stays attached properly
                if not value.startswith("$") and "currency" in final_struct:
                    value = f"{final_struct['currency'].strip()} {value}"
                final_struct[key] = value

        st.subheader("📋 Extracted Invoice Information")
        st.json(final_struct)

        # Flatten rows for export
        if isinstance(final_struct, dict):
            items = final_struct.get("items")
            base = {k: v for k, v in final_struct.items() if k not in ["items", "notes"]}

            if isinstance(items, list) and items:
                for it in items:
                    row = base.copy()
                    if isinstance(it, dict):
                        for k, v in it.items():
                            row[f"item_{k}"] = v
                    row["source_file"] = f.name
                    all_rows.append(row)
            else:
                row = base.copy()
                row["source_file"] = f.name
                all_rows.append(row)
        else:
            all_rows.append({"source_file": f.name, "raw": str(final_struct)})

        summaries.append({"file": f.name, "summary": gemini_summary or ""})

    # -------- Combine and Export Section --------
    st.divider()
    st.header("💾 Export Results")

    # Combine multiple rows for same invoice (merge items)
    grouped = {}
    for entry in all_rows:
        inv_no = entry.get("invoice_number") or entry.get("source_file")
        if inv_no not in grouped:
            grouped[inv_no] = {
                "invoice_number": entry.get("invoice_number", ""),
                "vendor": entry.get("vendor", ""),
                "date": entry.get("date", ""),
                "buyer": entry.get("buyer", ""),
                "address": entry.get("address", ""),
                "subtotal": entry.get("subtotal", ""),
                "tax": entry.get("tax", ""),
                "grand_total": entry.get("grand_total", ""),
                "source_file": entry.get("source_file", ""),
                "item_descriptions": []
            }

        # Collect item descriptions
        for key in entry.keys():
            if key.startswith("item_description"):
                grouped[inv_no]["item_descriptions"].append(str(entry[key]).strip())

    combined_invoices = []
    for inv_no, data in grouped.items():
        data["item_description"] = "; ".join(data["item_descriptions"])
        del data["item_descriptions"]
        if "notes" in data:
            del data["notes"]
        combined_invoices.append(data)

    df = pd.DataFrame(combined_invoices)

    # Fix currency formatting (ensure $ always with numbers)
    def normalize_currency(val):
        if isinstance(val, str) and val.strip():
            val = val.replace(",", ".").strip()
            if not val.startswith("$") and df.get("currency") is not None:
                return f"{df.at[0, 'currency']} {val}"
        return val

    for col in ["subtotal", "tax", "grand_total"]:
        if col in df.columns:
            df[col] = df[col].apply(normalize_currency)

    st.write("### Combined table (preview)")
    st.dataframe(df.head(50))

    # --- Export files ---
    csv_data = df.to_csv(index=False).encode("utf-8")
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")

    st.download_button("📥 Download CSV", data=csv_data, file_name="invoices_extracted.csv", mime="text/csv")
    st.download_button("📘 Download Excel", data=excel_buffer, file_name="invoices_extracted.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Save automatically
    df.to_csv("outputs/all_invoices_export.csv", index=False)
    with open("outputs/summaries.json", "w", encoding="utf-8") as f:
        json_summaries = {s["file"]: s["summary"] for s in summaries}
        f.write(json.dumps(json_summaries, indent=2))

    st.success("✅ All outputs saved to ./outputs/")
