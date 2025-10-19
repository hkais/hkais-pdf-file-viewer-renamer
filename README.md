# PDF Viewer & Renamer

A Python desktop application for viewing and renaming PDF files with a focus on inspection document workflows.

## Features

- **Folder Selection**: Browse and select any folder containing PDF files
- **PDF List View**: See all PDFs in the selected folder at a glance
- **First Page Preview**: View the first page of any selected PDF in high quality
- **Quick Rename**: Quickly prepend an inspection number to PDF filenames
- **Standard Rename**: Full control to rename files however you want
- **User-Friendly Interface**: Clean, intuitive GUI built with tkinter

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. **Clone or download this repository**

2. **Install required dependencies:**

```bash
pip install -r requirements.txt
```

This will install:
- PyMuPDF (fitz) - For PDF rendering
- Pillow (PIL) - For image processing

## Usage

### Starting the Application

Run the application with:

```bash
python app.py
```

### Using the Application

1. **Select a Folder**
   - Click the "Select Folder" button at the top
   - Choose a folder containing PDF files
   - All PDFs in that folder will be listed on the left side

2. **Preview a PDF**
   - Click on any PDF filename in the list
   - The first page will be displayed in the preview panel on the right
   - If the preview is large, you can scroll to see the entire page

3. **Quick Rename (Inspection Number)**
   - Select a PDF from the list
   - Review the preview to identify the inspection number
   - Click "Quick Rename (Inspection #)" button
   - Enter the inspection number when prompted
   - The file will be renamed with the inspection number prepended
   - Example: `report.pdf` → `12345_report.pdf`

4. **Standard Rename**
   - Select a PDF from the list
   - Click "Standard Rename" button
   - Enter the new filename (without .pdf extension)
   - The file will be renamed accordingly

### Tips

- The file list automatically refreshes after renaming
- The renamed file remains selected for easy verification
- Invalid characters are automatically removed from filenames
- You'll be warned if a file with the new name already exists

## Technical Details

- **GUI Framework**: tkinter (built-in with Python)
- **PDF Processing**: PyMuPDF (fitz)
- **Image Handling**: Pillow (PIL)
- **Supported Format**: PDF files only

## Troubleshooting

**Issue**: "No module named 'fitz'" error
- **Solution**: Run `pip install PyMuPDF`

**Issue**: Preview shows error
- **Solution**: Ensure the PDF file is not corrupted and is a valid PDF format

**Issue**: Application window is too small/large
- **Solution**: The window size is 1200x700 by default. You can resize it manually or modify the `self.root.geometry("1200x700")` line in `app.py`

## Requirements

See `requirements.txt` for exact version requirements:
- PyMuPDF==1.23.8
- Pillow==10.1.0

## License

This project is provided as-is for personal or commercial use.
