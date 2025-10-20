import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import os
import re

# Try to import pytesseract, but make it optional
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None

class PDFViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("מציג ומשנה שמות PDF")
        self.root.geometry("1200x700")
        
        self.current_folder = None
        self.pdf_files = []
        self.selected_pdf = None
        self.current_preview_image = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the user interface"""
        # Top frame for folder selection
        top_frame = tk.Frame(self.root, padx=10, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Button on the right side for RTL
        tk.Button(top_frame, text="בחר תיקייה", command=self.select_folder, 
                 font=("Arial", 12), bg="#4CAF50", fg="white", padx=20, pady=5).pack(side=tk.RIGHT)
        
        self.folder_label = tk.Label(top_frame, text="לא נבחרה תיקייה", 
                                     font=("Arial", 10), fg="gray")
        self.folder_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content - use PanedWindow for resizable columns
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        self.paned_window.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Right panel - PDF list (RTL: list on right)
        right_frame = tk.Frame(self.paned_window)
        
        tk.Label(right_frame, text="קבצי PDF", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Listbox with scrollbar
        list_frame = tk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        # Create listbox with increased line spacing and custom styling
        self.pdf_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                      font=("Arial", 13), selectmode=tk.SINGLE,
                                      height=15,  # Set initial height for better spacing
                                      activestyle='none')  # Remove default selection highlight
        self.pdf_listbox.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.pdf_listbox.bind('<<ListboxSelect>>', self.on_pdf_select)
        
        scrollbar.config(command=self.pdf_listbox.yview)
        
        # Rename buttons
        button_frame = tk.Frame(right_frame)
        button_frame.pack(pady=10, fill=tk.X)
        
        tk.Button(button_frame, text="שינוי שם מהיר\n(מספר בדיקה)", 
                 command=self.quick_rename, font=("Arial", 10), 
                 bg="#2196F3", fg="white", pady=5).pack(fill=tk.X, pady=2)
        
        tk.Button(button_frame, text="שינוי שם רגיל", 
                 command=self.standard_rename, font=("Arial", 10), 
                 bg="#FF9800", fg="white", pady=5).pack(fill=tk.X, pady=2)
        
        # Text extraction buttons (hidden for now, code kept for future use)
        # tk.Button(button_frame, text="חילוץ טקסט", 
        #          command=self.extract_text, font=("Arial", 10), 
        #          bg="#9C27B0", fg="white", pady=5).pack(fill=tk.X, pady=2)
        
        # tk.Button(button_frame, text="חילוץ עם OCR", 
        #          command=self.extract_text_with_ocr, font=("Arial", 10), 
        #          bg="#E91E63", fg="white", pady=5).pack(fill=tk.X, pady=2)
        
        # Left panel - PDF preview (RTL: preview on left)
        left_frame = tk.Frame(self.paned_window, bg="white", relief=tk.SUNKEN, borderwidth=2)
        
        tk.Label(left_frame, text="תצוגה מקדימה", font=("Arial", 12, "bold"), 
                bg="white").pack(pady=5)
        
        # Filename display
        self.filename_label = tk.Label(left_frame, text="", font=("Arial", 10), 
                                      bg="white", fg="#666666")
        self.filename_label.pack(pady=(0, 5))
        
        # Horizontal separator
        separator = ttk.Separator(left_frame, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=5)
        
        # Canvas for PDF preview with scrollbar
        preview_frame = tk.Frame(left_frame, bg="white")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        preview_scrollbar = tk.Scrollbar(preview_frame)
        preview_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="white", 
                                       yscrollcommand=preview_scrollbar.set)
        self.preview_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        preview_scrollbar.config(command=self.preview_canvas.yview)
        
        self.preview_label = tk.Label(self.preview_canvas, text="בחר קובץ PDF לתצוגה מקדימה", 
                                     font=("Arial", 14), fg="gray", bg="white")
        self.preview_canvas.create_window(400, 300, window=self.preview_label)
        
        # Add frames to paned window with minimum sizes (reversed order for RTL)
        self.paned_window.add(left_frame, minsize=400)
        self.paned_window.add(right_frame, minsize=200)
        
        # Set initial sash position: file list (right) takes 1/3 of width
        # Window is 1200px, with 20px padding = ~1180px usable
        # Position sash at ~787px from left (2/3) so right panel is ~393px (1/3)
        # Use after() to delay until window is fully rendered
        self.root.after(100, lambda: self.paned_window.sash_place(0, 787, 1))
        
    def select_folder(self):
        """Open folder selection dialog"""
        folder_path = filedialog.askdirectory(title="בחר תיקייה עם קבצי PDF")
        
        if folder_path:
            self.current_folder = Path(folder_path)
            self.folder_label.config(text=f"תיקייה: {folder_path}")
            self.load_pdf_files()
    
    def has_inspection_number(self, filename):
        """Check if filename already has an inspection number pattern"""
        # Pattern: starts with digits followed by underscore
        import re
        pattern = r'^\d+_.*\.pdf$'
        return bool(re.match(pattern, filename))
    
    def load_pdf_files(self, clear_preview=True):
        """Load all PDF files from the selected folder
        Args:
            clear_preview: Whether to clear the preview (True for folder changes, False for refreshes)
        """
        if not self.current_folder:
            return
        
        self.pdf_files = sorted([f for f in self.current_folder.iterdir() 
                                if f.suffix.lower() == '.pdf'])
        
        # Update listbox with conditional styling
        self.pdf_listbox.delete(0, tk.END)
        for pdf_file in self.pdf_files:
            self.pdf_listbox.insert(tk.END, pdf_file.name)
        
        # Apply conditional styling after all items are inserted
        for i, pdf_file in enumerate(self.pdf_files):
            if self.has_inspection_number(pdf_file.name):
                # Files with inspection numbers get green text
                self.pdf_listbox.itemconfig(i, {'fg': '#2E7D32'})  # Dark green
            else:
                # Files without inspection numbers get default black text
                self.pdf_listbox.itemconfig(i, {'fg': '#000000'})
        
        # Only clear preview when explicitly requested (e.g., folder change)
        if clear_preview:
            self.filename_label.config(text="")
            self.preview_canvas.delete("all")
            self.preview_label = tk.Label(self.preview_canvas, text="בחר קובץ PDF לתצוגה מקדימה", 
                                         font=("Arial", 14), fg="gray", bg="white")
            self.preview_canvas.create_window(400, 300, window=self.preview_label)
        
        if not self.pdf_files:
            messagebox.showinfo("לא נמצאו קבצי PDF", 
                              "לא נמצאו קבצי PDF בתיקייה שנבחרה.",
                              parent=self.root)
    
    def on_pdf_select(self, event):
        """Handle PDF selection from list"""
        selection = self.pdf_listbox.curselection()
        if selection:
            index = selection[0]
            self.selected_pdf = self.pdf_files[index]
            self.preview_pdf()
    
    def preview_pdf(self):
        """Render and display the first page of the selected PDF"""
        if not self.selected_pdf:
            return
        
        try:
            # Update filename display
            self.filename_label.config(text=self.selected_pdf.name)
            
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(self.selected_pdf)
            
            # Get the first page
            first_page = pdf_document[0]
            
            # Render page to image (increase resolution for better quality)
            zoom = 2.0  # Zoom factor for better quality
            mat = fitz.Matrix(zoom, zoom)
            pix = first_page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Resize if too large (max width 800px)
            max_width = 800
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage for tkinter
            self.current_preview_image = ImageTk.PhotoImage(img)
            
            # Clear canvas and display image
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(10, 10, anchor=tk.NW, 
                                           image=self.current_preview_image)
            
            # Update scroll region
            self.preview_canvas.config(scrollregion=self.preview_canvas.bbox("all"))
            
            pdf_document.close()
            
        except Exception as e:
            messagebox.showerror("שגיאת תצוגה מקדימה", 
                               f"לא ניתן להציג את קובץ ה-PDF:\n{str(e)}",
                               parent=self.root)
            self.preview_canvas.delete("all")
            error_label = tk.Label(self.preview_canvas, 
                                  text=f"שגיאה בטעינת PDF:\n{str(e)}", 
                                  font=("Arial", 12), fg="red", bg="white")
            self.preview_canvas.create_window(400, 300, window=error_label)
    
    def quick_rename(self):
        """Quick rename with inspection number prepended"""
        if not self.selected_pdf:
            messagebox.showwarning("לא נבחר קובץ", 
                                  "אנא בחר קובץ PDF תחילה.",
                                  parent=self.root)
            return
        
        # Use custom positioned dialog
        inspection_num = self.create_quick_rename_dialog()
        
        if not inspection_num:
            return  # User cancelled
        
        # Clean the inspection number (remove invalid characters)
        inspection_num = "".join(c for c in inspection_num 
                                if c.isalnum() or c in ('-', '_'))
        
        if not inspection_num:
            messagebox.showerror("קלט לא תקין", 
                               "מספר הבדיקה לא יכול להיות רק תווים מיוחדים.",
                               parent=self.root)
            return
        
        # Create new filename
        original_name = self.selected_pdf.name
        new_name = f"{inspection_num}_{original_name}"
        new_path = self.selected_pdf.parent / new_name
        
        # Check if file already exists
        if new_path.exists():
            if not messagebox.askyesno("הקובץ קיים", 
                                      f"קובץ בשם '{new_name}' כבר קיים.\nלהחליף אותו?",
                                      parent=self.root):
                return
        
        try:
            # Rename the file
            self.selected_pdf.rename(new_path)
            
            # Update internal state
            old_index = self.pdf_files.index(self.selected_pdf)
            self.selected_pdf = new_path
            
            # Reload file list without clearing preview
            self.load_pdf_files(clear_preview=False)
            
            # Reselect the renamed file
            new_index = self.pdf_files.index(self.selected_pdf)
            self.pdf_listbox.selection_clear(0, tk.END)
            self.pdf_listbox.selection_set(new_index)
            self.pdf_listbox.see(new_index)
            
            # Update filename display and refresh preview
            self.filename_label.config(text=self.selected_pdf.name)
            self.preview_pdf()  # Refresh the preview
            
            messagebox.showinfo("הצלחה", f"שם הקובץ שונה ל:\n{new_name}",
                              parent=self.root)
            
        except Exception as e:
            messagebox.showerror("שגיאה בשינוי שם", 
                               f"לא ניתן לשנות את שם הקובץ:\n{str(e)}",
                               parent=self.root)

    def extract_text(self):
        """Extract text from the selected PDF and find inspection numbers using optimized detection"""
        if not self.selected_pdf:
            messagebox.showwarning("לא נבחר קובץ", 
                                  "אנא בחר קובץ PDF תחילה.",
                                  parent=self.root)
            return
        
        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(self.selected_pdf)
            first_page = pdf_document[0]
            
            # Extract text with detailed information (font size, color, etc.)
            text_blocks = first_page.get_text("dict")
            
            # Extract text from optimized top-left region (30% height, 50% width)
            page_width = first_page.rect.width
            page_height = first_page.rect.height
            top_left_rect = fitz.Rect(0, 0, page_width * 0.5, page_height * 0.3)
            top_left_text_blocks = []
            
            # Filter blocks that are in the top-left region
            for block in text_blocks["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            bbox = fitz.Rect(span["bbox"])
                            if bbox.intersects(top_left_rect):
                                top_left_text_blocks.append(span)
            
            # Find inspection numbers using optimized criteria
            inspection_candidates = []
            all_red_text = []
            
            for span in top_left_text_blocks:
                # Check for red color (RGB values near 255,0,0)
                is_red = False
                if "color" in span:
                    # PyMuPDF stores color as RGB integer, convert to separate components
                    color_int = span["color"]
                    r = (color_int >> 16) & 0xFF
                    g = (color_int >> 8) & 0xFF
                    b = color_int & 0xFF
                    
                    # Check if text is red (high red component, low green and blue)
                    if r > 200 and g < 100 and b < 100:
                        is_red = True
                        all_red_text.append(span)
                
                # Extract 5-6 digit numbers from text
                import re
                inspection_pattern = r'\b\d{5,6}\b'  # Specifically 5-6 digits
                numbers_in_span = re.findall(inspection_pattern, span["text"])
                
                for number in numbers_in_span:
                    inspection_candidates.append({
                        "number": number,
                        "font_size": span["size"],
                        "is_red": is_red,
                        "text": span["text"],
                        "bbox": span["bbox"],
                        "is_perfect_match": is_red and len(number) >= 5  # Perfect match criteria
                    })
            
            # Prioritize perfect matches (red text, 5-6 digits)
            perfect_matches = [c for c in inspection_candidates if c["is_perfect_match"]]
            other_candidates = [c for c in inspection_candidates if not c["is_perfect_match"]]
            
            # Sort perfect matches by font size (larger first)
            perfect_matches.sort(key=lambda x: x["font_size"], reverse=True)
            other_candidates.sort(key=lambda x: x["font_size"], reverse=True)
            
            # Combine results with perfect matches first
            final_candidates = perfect_matches + other_candidates
            
            # Get regular text for display
            full_text = first_page.get_text()
            top_left_text = first_page.get_text("text", clip=top_left_rect)
            
            pdf_document.close()
            
            # Show optimized results
            self.show_optimized_extraction_results(full_text, top_left_text, final_candidates, 
                                                 all_red_text, top_left_rect, page_width, page_height)
            
        except Exception as e:
            messagebox.showerror("שגיאה בחילוץ טקסט", 
                               f"לא ניתן לחלץ טקסט מהקובץ:\n{str(e)}",
                               parent=self.root)
    
    def extract_text_with_ocr(self):
        """Extract text from scanned PDF using OCR with improved detection"""
        if not self.selected_pdf:
            messagebox.showwarning("לא נבחר קובץ", 
                                  "אנא בחר קובץ PDF תחילה.",
                                  parent=self.root)
            return
        
        # Check if OCR is available
        if not OCR_AVAILABLE:
            self.show_ocr_installation_guide()
            return
        
        # Verify Tesseract is accessible
        try:
            import subprocess
            result = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                messagebox.showerror("שגיאת OCR", 
                                   "Tesseract OCR מותקן אך לא נגיש.\n"
                                   "ודא ש-Tesseract נמצא ב-PATH.\n"
                                   f"שגיאה: {result.stderr}",
                                   parent=self.root)
                return
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            messagebox.showerror("שגיאת OCR", 
                               "Tesseract OCR לא נמצא ב-PATH.\n"
                               "התקן את Tesseract OCR והוסף אותו ל-PATH.\n"
                               f"פרטים: {str(e)}",
                               parent=self.root)
            return
        except Exception as e:
            messagebox.showerror("שגיאת OCR", 
                               f"בעיה בבדיקת Tesseract:\n{str(e)}",
                               parent=self.root)
            return
        
        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(self.selected_pdf)
            first_page = pdf_document[0]
            
            # Get page dimensions
            page_width = first_page.rect.width
            page_height = first_page.rect.height
            
            # Use the same optimized region as regular extraction (30% height, 50% width)
            top_left_rect = fitz.Rect(0, 0, page_width * 0.5, page_height * 0.3)
            
            # Render the page to image with high resolution
            zoom = 4.0  # Higher zoom for better OCR accuracy
            mat = fitz.Matrix(zoom, zoom)
            pix = first_page.get_pixmap(matrix=mat, clip=top_left_rect)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Enhanced preprocessing for better OCR
            # Convert to grayscale
            img_gray = img.convert('L')
            
            # Apply multiple preprocessing techniques
            processed_images = []
            
            # 1. Basic threshold
            threshold = 128
            img_binary = img_gray.point(lambda p: p > threshold and 255)
            processed_images.append(("בסיסי", img_binary))
            
            # 2. Adaptive threshold simulation (multiple levels)
            for thresh in [100, 150, 180]:
                img_adaptive = img_gray.point(lambda p: p > thresh and 255)
                processed_images.append((f"סף {thresh}", img_adaptive))
            
            # 3. Inverted (for light text on dark background)
            img_inverted = img_gray.point(lambda p: 255 - p)
            processed_images.append(("הפוך", img_inverted))
            
            # Try OCR on each processed image
            all_ocr_results = []
            
            for proc_name, proc_img in processed_images:
                try:
                    # Configure Tesseract for digit recognition
                    digit_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
                    general_config = r'--oem 3 --psm 6'
                    
                    # Extract digits only
                    digit_text = pytesseract.image_to_string(proc_img, config=digit_config)
                    
                    # Extract general text for context
                    general_text = pytesseract.image_to_string(proc_img, config=general_config)
                    
                    all_ocr_results.append({
                        "process_name": proc_name,
                        "digit_text": digit_text,
                        "general_text": general_text,
                        "image": proc_img
                    })
                    
                except Exception as e:
                    # Continue with other preprocessing methods
                    continue
            
            # Find 5-6 digit numbers across all OCR results
            numeric_pattern = r'\b\d{5,6}\b'
            all_numbers = []
            
            for result in all_ocr_results:
                numbers_in_digits = re.findall(numeric_pattern, result["digit_text"])
                numbers_in_general = re.findall(numeric_pattern, result["general_text"])
                
                for number in numbers_in_digits + numbers_in_general:
                    all_numbers.append({
                        "number": number,
                        "process": result["process_name"],
                        "text": result["digit_text"] if number in result["digit_text"] else result["general_text"]
                    })
            
            # Remove duplicates and score
            unique_numbers = {}
            for item in all_numbers:
                num = item["number"]
                if num not in unique_numbers:
                    unique_numbers[num] = {
                        "number": num,
                        "processes": [],
                        "score": 0,
                        "text_samples": []
                    }
                
                unique_numbers[num]["processes"].append(item["process"])
                unique_numbers[num]["text_samples"].append(item["text"])
            
            # Score numbers
            scored_numbers = []
            for num, data in unique_numbers.items():
                score = 0
                
                # Prefer numbers found in multiple preprocessing methods
                score += len(set(data["processes"])) * 20
                
                # Prefer numbers found in digit-only extraction
                if any("digits" in proc for proc in data["processes"]):
                    score += 30
                
                # Position scoring (earlier in text is better)
                for text_sample in data["text_samples"]:
                    position = text_sample.find(num)
                    if position >= 0:
                        score += max(0, 50 - position // 10)
                
                scored_numbers.append({
                    "number": data["number"],
                    "score": score,
                    "processes": data["processes"],
                    "text_samples": data["text_samples"]
                })
            
            # Sort by score (descending)
            scored_numbers.sort(key=lambda x: x["score"], reverse=True)
            
            pdf_document.close()
            
            # Show enhanced OCR results
            self.show_enhanced_ocr_results(scored_numbers, all_ocr_results, top_left_rect)
            
        except Exception as e:
            messagebox.showerror("שגיאה בחילוץ טקסט עם OCR", 
                               f"לא ניתן לחלץ טקסט עם OCR:\n{str(e)}",
                               parent=self.root)
    
    def show_ocr_installation_guide(self):
        """Show installation guide for OCR functionality"""
        dialog = tk.Toplevel(self.root)
        dialog.title("התקנת OCR")
        dialog.transient(self.root)
        
        # Position dialog near the buttons
        self.position_dialog_near_buttons(dialog, width=600, height=400)
        
        tk.Label(dialog, text="OCR לא מותקן", 
                font=("Arial", 14, "bold"), fg="#E91E63").pack(pady=10)
        
        instruction_text = """כדי להשתמש בחילוץ טקסט עם OCR, יש להתקין את החבילות הבאות:

1. התקנת pytesseract:
   ```bash
   pip install pytesseract
   ```

2. התקנת Tesseract OCR:
   - הורד מהקישור: https://github.com/UB-Mannheim/tesseract/wiki
   - הרץ את הקובץ tesseract-ocr-w64-setup-5.3.3.20231005.exe
   - ודא ש-Tesseract נוסף ל-PATH (בדרך כלל: C:\\Program Files\\Tesseract-OCR\\)

3. הפעל מחדש את האפליקציה

לאחר ההתקנה, לחץ שוב על כפתור 'חילוץ עם OCR'."""
        
        text_widget = tk.Text(dialog, wrap=tk.WORD, height=15, font=("Arial", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        text_widget.insert(tk.END, instruction_text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="סגור", command=dialog.destroy,
                 font=("Arial", 10), bg="#607D8B", fg="white",
                 padx=20, pady=5).pack()
        
        # Make dialog modal
        dialog.grab_set()
    
    def show_enhanced_ocr_results(self, scored_numbers, all_ocr_results, top_left_rect):
        """Display enhanced OCR extraction results with multiple preprocessing methods"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("תוצאות חילוץ OCR משופר")
        dialog.transient(self.root)
        
        # Set RTL orientation for the dialog
        dialog.tk.call('tk', 'scaling', 1.0)  # Ensure proper scaling
        dialog.configure(bg='white')
        
        # Position dialog near the buttons
        self.position_dialog_near_buttons(dialog, width=350, height=600)
        
        # Create main frame with RTL support
        main_frame = tk.Frame(dialog, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Create notebook for tabs with RTL support
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Inspection Numbers (Primary Results)
        inspection_frame = tk.Frame(notebook, bg='white')
        notebook.add(inspection_frame, text="מספרי בדיקה")
        
        # Statistics header with RTL layout
        stats_frame = tk.Frame(inspection_frame, bg='white')
        stats_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(stats_frame, text=f"שיטות עיבוד: {len(all_ocr_results)}", 
                font=("Arial", 10), bg='white').pack(side=tk.RIGHT, padx=5)
        tk.Label(stats_frame, text=f"אזור חיפוש: 30% גובה, 50% רוחב", 
                font=("Arial", 10), bg='white').pack(side=tk.RIGHT, padx=5)
        
        if scored_numbers:
            result_label = tk.Label(inspection_frame, text="✅ מספרי בדיקה שזוהו עם OCR:", 
                                  font=("Arial", 12, "bold"), fg="#2E7D32", bg='white')
            result_label.pack(anchor=tk.E, pady=(10, 5), padx=15)
        else:
            result_label = tk.Label(inspection_frame, text="⚠️ לא נמצאו מספרי בדיקה עם OCR", 
                                  font=("Arial", 12, "bold"), fg="#F57C00", bg='white')
            result_label.pack(anchor=tk.E, pady=(10, 5), padx=15)
        
        # Create scrollable frame for candidates with RTL support
        canvas = tk.Canvas(inspection_frame, bg='white', highlightthickness=0)
        scrollbar = tk.Scrollbar(inspection_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Display candidates
        if scored_numbers:
            for i, candidate in enumerate(scored_numbers):
                candidate_frame = tk.Frame(scrollable_frame, relief=tk.GROOVE, borderwidth=1)
                candidate_frame.pack(fill=tk.X, padx=5, pady=2)
                
                # Color code based on score
                if candidate["score"] >= 70:
                    bg_color = "#E8F5E8"  # Light green
                    indicator = "✅"
                elif candidate["score"] >= 40:
                    bg_color = "#FFF3E0"  # Light orange
                    indicator = "⚠️"
                else:
                    bg_color = "#FFEBEE"  # Light red
                    indicator = "❌"
                
                candidate_frame.config(bg=bg_color)
                
                # Number and indicator
                number_frame = tk.Frame(candidate_frame, bg=bg_color)
                number_frame.pack(fill=tk.X, padx=10, pady=5)
                
                tk.Label(number_frame, text=f"{indicator} {i+1}. {candidate['number']}", 
                        font=("Arial", 12, "bold"), bg=bg_color,
                        fg="#2E7D32" if candidate["score"] >= 70 else "#F57C00").pack(side=tk.RIGHT)
                
                # Details
                details_frame = tk.Frame(candidate_frame, bg=bg_color)
                details_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
                
                tk.Label(details_frame, text=f"ציון: {candidate['score']}", 
                        font=("Arial", 9), bg=bg_color).pack(side=tk.RIGHT, padx=5)
                
                processes_str = ", ".join(candidate["processes"])
                tk.Label(details_frame, text=f"שיטות: {processes_str}", 
                        font=("Arial", 9), bg=bg_color).pack(side=tk.RIGHT, padx=5)
                
                # Use button
                use_button = tk.Button(candidate_frame, text="השתמש במספר זה",
                                     command=lambda num=candidate['number']: self.use_ocr_number(num, dialog),
                                     font=("Arial", 9), bg="#4CAF50", fg="white")
                use_button.pack(pady=5)
        else:
            tk.Label(scrollable_frame, text="לא נמצאו מספרים באף שיטת עיבוד", 
                    font=("Arial", 10)).pack(pady=20)
            tk.Label(scrollable_frame, text="נסה את חילוץ הטקסט הרגיל אם הקובץ אינו סרוק", 
                    font=("Arial", 9), fg="gray").pack(pady=5)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tab 2: OCR Processing Details
        processing_frame = tk.Frame(notebook, bg='white')
        notebook.add(processing_frame, text="פירוט עיבוד")
        
        tk.Label(processing_frame, text="תוצאות לפי שיטת עיבוד תמונה:", 
                font=("Arial", 12, "bold"), bg='white').pack(anchor=tk.E, pady=(15, 10), padx=15)
        
        # Create scrollable frame for processing details with RTL support
        proc_canvas = tk.Canvas(processing_frame, bg='white', highlightthickness=0)
        proc_scrollbar = tk.Scrollbar(processing_frame, orient=tk.VERTICAL, command=proc_canvas.yview)
        proc_scrollable_frame = tk.Frame(proc_canvas, bg='white')
        
        proc_scrollable_frame.bind(
            "<Configure>",
            lambda e: proc_canvas.configure(scrollregion=proc_canvas.bbox("all"))
        )
        
        proc_canvas.create_window((0, 0), window=proc_scrollable_frame, anchor="nw")
        proc_canvas.configure(yscrollcommand=proc_scrollbar.set)
        
        for result in all_ocr_results:
            method_frame = tk.Frame(proc_scrollable_frame, relief=tk.GROOVE, borderwidth=1)
            method_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(method_frame, text=f"שיטה: {result['process_name']}", 
                    font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=5)
            
            # Digit text
            tk.Label(method_frame, text="טקסט ספרות בלבד:", 
                    font=("Arial", 9)).pack(anchor=tk.W, padx=10)
            digit_textbox = tk.Text(method_frame, wrap=tk.WORD, height=3, font=("Courier New", 8))
            digit_textbox.pack(fill=tk.X, padx=10, pady=(0, 5))
            digit_textbox.insert(tk.END, result["digit_text"] if result["digit_text"].strip() else "לא נמצא טקסט")
            digit_textbox.config(state=tk.DISABLED)
            
            # General text
            tk.Label(method_frame, text="טקסט כללי:", 
                    font=("Arial", 9)).pack(anchor=tk.W, padx=10)
            general_textbox = tk.Text(method_frame, wrap=tk.WORD, height=3, font=("Courier New", 8))
            general_textbox.pack(fill=tk.X, padx=10, pady=(0, 5))
            general_textbox.insert(tk.END, result["general_text"] if result["general_text"].strip() else "לא נמצא טקסט")
            general_textbox.config(state=tk.DISABLED)
        
        proc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        proc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tab 3: OCR Debug Information
        debug_frame = tk.Frame(notebook, bg='white')
        notebook.add(debug_frame, text="מידע לאיתור בעיות")
        
        tk.Label(debug_frame, text="מידע לאיתור בעיות ב-OCR:", 
                font=("Arial", 12, "bold"), bg='white').pack(anchor=tk.E, pady=(15, 10), padx=15)
        
        # Create scrollable debug text area with RTL support
        debug_canvas = tk.Canvas(debug_frame, bg='white', highlightthickness=0)
        debug_scrollbar = tk.Scrollbar(debug_frame, orient=tk.VERTICAL, command=debug_canvas.yview)
        debug_scrollable_frame = tk.Frame(debug_canvas, bg='white')
        
        debug_scrollable_frame.bind(
            "<Configure>",
            lambda e: debug_canvas.configure(scrollregion=debug_canvas.bbox("all"))
        )
        
        debug_canvas.create_window((0, 0), window=debug_scrollable_frame, anchor="nw")
        debug_canvas.configure(yscrollcommand=debug_scrollbar.set)
        
        debug_textbox = tk.Text(debug_scrollable_frame, wrap=tk.WORD, height=25, 
                               font=("Courier New", 10), bg='white')
        debug_textbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        debug_info = """טיפים לשיפור תוצאות ה-OCR:

1. אם לא נמצאו מספרים:
   ✓ בדוק אם המספר באמת נמצא באזור החיפוש (30% גובה, 50% רוחב)
   ✓ ודא שהמספר הוא בעל 5-6 ספרות
   ✓ הקובץ עשוי להיות מסוג שדורש עיבוד שונה

2. אם נמצאו מספרים שגויים:
   ✓ התמונה עשויה להיות באיכות נמוכה
   ✓ ייתכן שהמספר אינו בצבע אדום בולט
   ✓ המספר עשוי להיות קטן מדי או מעוות

3. המלצות:
   ✓ נסה חילוץ טקסט רגיל קודם (לקבצים שאינם סרוקים)
   ✓ בדוק את איכות המסמך המקורי
   ✓ המספר צריך להיות הטקסט האדום היחיד באזור

4. שיטות עיבוד שנוסו:
   ✓ בסיסי: סף ברירת מחדל (128)
   ✓ סף 100: רמת סף נמוכה לטקסט עמום
   ✓ סף 150: רמת סף בינונית לטקסט סטנדרטי
   ✓ סף 180: רמת סף גבוהה לטקסט בהיר
   ✓ הפוך: עבור טקסט בהיר על רקע כהה

5. פתרונות אפשריים:
   ✓ נסה את חילוץ הטקסט הרגיל (ללא OCR)
   ✓ בדוק את איכות הסריקה המקורית
   ✓ ודא שהמספר ברור וקריא
   ✓ הגדל את רזולוציית הסריקה אם אפשר

6. טיפים מתקדמים:
   ✓ המספר צריך להיות הטקסט האדום היחיד באזור
   ✓ גודל הפונט של המספר צריך להיות גדול מהטקסט הסמוך
   ✓ המספר צריך להיות בפינה השמאלית העליונה של הדף
"""
        
        debug_textbox.insert(tk.END, debug_info)
        debug_textbox.config(state=tk.DISABLED)
        
        debug_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        debug_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Close button with better styling
        button_frame = tk.Frame(dialog, bg='white')
        button_frame.pack(pady=15)
        
        tk.Button(button_frame, text="סגור", command=dialog.destroy,
                 font=("Arial", 11, "bold"), bg="#607D8B", fg="white",
                 padx=30, pady=8, relief=tk.RAISED, bd=2).pack()
        
        # Make dialog modal
        dialog.grab_set()
    
    def use_ocr_number(self, number, dialog):
        """Use the selected OCR number for renaming"""
        dialog.destroy()
        # Set the number in a quick rename dialog
        self.perform_quick_rename_with_number(number)
    
    def perform_quick_rename_with_number(self, inspection_num):
        """Perform quick rename with the provided inspection number"""
        if not self.selected_pdf:
            return
        
        # Create new filename
        original_name = self.selected_pdf.name
        new_name = f"{inspection_num}_{original_name}"
        new_path = self.selected_pdf.parent / new_name
        
        # Check if file already exists
        if new_path.exists():
            if not messagebox.askyesno("הקובץ קיים", 
                                      f"קובץ בשם '{new_name}' כבר קיים.\nלהחליף אותו?",
                                      parent=self.root):
                return
        
        try:
            # Rename the file
            self.selected_pdf.rename(new_path)
            
            # Update internal state
            old_index = self.pdf_files.index(self.selected_pdf)
            self.selected_pdf = new_path
            
            # Reload file list without clearing preview
            self.load_pdf_files(clear_preview=False)
            
            # Reselect the renamed file
            new_index = self.pdf_files.index(self.selected_pdf)
            self.pdf_listbox.selection_clear(0, tk.END)
            self.pdf_listbox.selection_set(new_index)
            self.pdf_listbox.see(new_index)
            
            # Update filename display and refresh preview
            self.filename_label.config(text=self.selected_pdf.name)
            self.preview_pdf()  # Refresh the preview
            
            messagebox.showinfo("הצלחה", f"שם הקובץ שונה ל:\n{new_name}",
                              parent=self.root)
            
        except Exception as e:
            messagebox.showerror("שגיאה בשינוי שם", 
                               f"לא ניתן לשנות את שם הקובץ:\n{str(e)}",
                               parent=self.root)
    
    def show_extraction_results(self, full_text, top_left_text, potential_numbers, contextual_numbers):
        """Display extracted text and potential inspection numbers"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("תוצאות חילוץ טקסט")
        dialog.transient(self.root)
        
        # Position dialog near the buttons
        self.position_dialog_near_buttons(dialog, width=350, height=600)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Top-left text
        top_left_frame = tk.Frame(notebook)
        notebook.add(top_left_frame, text="טקסט מהפינה השמאלית העליונה")
        
        tk.Label(top_left_frame, text="טקסט שחולץ מהפינה השמאלית העליונה:", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        top_left_textbox = tk.Text(top_left_frame, wrap=tk.WORD, height=8, font=("Arial", 9))
        top_left_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        top_left_textbox.insert(tk.END, top_left_text if top_left_text else "לא נמצא טקסט")
        top_left_textbox.config(state=tk.DISABLED)
        
        # Tab 2: Potential numbers
        numbers_frame = tk.Frame(notebook)
        notebook.add(numbers_frame, text="מספרים פוטנציאליים")
        
        tk.Label(numbers_frame, text="מספרים פוטנציאליים לבדיקה:", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        numbers_text = tk.Text(numbers_frame, wrap=tk.WORD, height=8, font=("Arial", 9))
        numbers_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        if potential_numbers:
            numbers_text.insert(tk.END, "מספרים שנמצאו בפינה השמאלית העליונה:\n")
            for num in set(potential_numbers):  # Remove duplicates
                numbers_text.insert(tk.END, f"- {num}\n")
            
            if contextual_numbers:
                numbers_text.insert(tk.END, "\nמספרים שנמצאו ליד מילות מפתח:\n")
                for num in set(contextual_numbers):
                    numbers_text.insert(tk.END, f"- {num}\n")
        else:
            numbers_text.insert(tk.END, "לא נמצאו מספרים פוטנציאליים")
        
        numbers_text.config(state=tk.DISABLED)
        
        # Tab 3: Full text (optional)
        full_frame = tk.Frame(notebook)
        notebook.add(full_frame, text="כל הטקסט")
        
        tk.Label(full_frame, text="כל הטקסט מהדף הראשון:", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        full_textbox = tk.Text(full_frame, wrap=tk.WORD, height=8, font=("Arial", 9))
        full_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        full_textbox.insert(tk.END, full_text if full_text else "לא נמצא טקסט")
        full_textbox.config(state=tk.DISABLED)
        
        # Close button
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="סגור", command=dialog.destroy,
                 font=("Arial", 10), bg="#607D8B", fg="white",
                 padx=20, pady=5).pack()
        
        # Make dialog modal
        dialog.grab_set()
    
    def show_optimized_extraction_results(self, full_text, top_left_text, final_candidates, 
                                        all_red_text, top_left_rect, page_width, page_height):
        """Display optimized extraction results with clear inspection number identification"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("תוצאות חילוץ ממוספרות בדיקה")
        dialog.transient(self.root)
        
        # Position dialog near the buttons
        self.position_dialog_near_buttons(dialog, width=350, height=600)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Inspection Numbers (Primary Results)
        inspection_frame = tk.Frame(notebook)
        notebook.add(inspection_frame, text="מספרי בדיקה")
        
        # Statistics header
        stats_frame = tk.Frame(inspection_frame)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(stats_frame, text=f"אזור חיפוש: 30% גובה, 50% רוחב", 
                font=("Arial", 9)).pack(side=tk.RIGHT, padx=5)
        tk.Label(stats_frame, text=f"טקסט אדום שנמצא: {len(all_red_text)}", 
                font=("Arial", 9)).pack(side=tk.RIGHT, padx=5)
        
        # Check for perfect matches
        perfect_matches = [c for c in final_candidates if c["is_perfect_match"]]
        
        if perfect_matches:
            tk.Label(inspection_frame, text="✅ מספרי בדיקה שזוהו (טקסט אדום, 5-6 ספרות):", 
                    font=("Arial", 11, "bold"), fg="#2E7D32").pack(anchor=tk.W, pady=(10, 5))
        else:
            tk.Label(inspection_frame, text="⚠️ לא נמצאו מספרי בדיקה מתאימים", 
                    font=("Arial", 11, "bold"), fg="#F57C00").pack(anchor=tk.W, pady=(10, 5))
        
        # Create scrollable frame for candidates
        canvas = tk.Canvas(inspection_frame)
        scrollbar = tk.Scrollbar(inspection_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Display candidates
        if final_candidates:
            for i, candidate in enumerate(final_candidates):
                candidate_frame = tk.Frame(scrollable_frame, relief=tk.GROOVE, borderwidth=1)
                candidate_frame.pack(fill=tk.X, padx=5, pady=2)
                
                # Color code based on match quality
                if candidate["is_perfect_match"]:
                    bg_color = "#E8F5E8"  # Light green
                    indicator = "✅"
                else:
                    bg_color = "#FFF3E0"  # Light orange
                    indicator = "⚠️"
                
                candidate_frame.config(bg=bg_color)
                
                # Number and indicator
                number_frame = tk.Frame(candidate_frame, bg=bg_color)
                number_frame.pack(fill=tk.X, padx=10, pady=5)
                
                tk.Label(number_frame, text=f"{indicator} {i+1}. {candidate['number']}", 
                        font=("Arial", 12, "bold"), bg=bg_color,
                        fg="#2E7D32" if candidate["is_perfect_match"] else "#F57C00").pack(side=tk.RIGHT)
                
                # Details
                details_frame = tk.Frame(candidate_frame, bg=bg_color)
                details_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
                
                tk.Label(details_frame, text=f"גודל פונט: {candidate['font_size']:.1f}", 
                        font=("Arial", 9), bg=bg_color).pack(side=tk.RIGHT, padx=5)
                
                color_indicator = "🔴" if candidate['is_red'] else "⚫"
                tk.Label(details_frame, text=f"צבע: {color_indicator}", 
                        font=("Arial", 9), bg=bg_color).pack(side=tk.RIGHT, padx=5)
                
                # Use button
                use_button = tk.Button(candidate_frame, text="השתמש במספר זה",
                                     command=lambda num=candidate['number']: self.use_extracted_number(num, dialog),
                                     font=("Arial", 9), bg="#4CAF50", fg="white")
                use_button.pack(pady=5)
        else:
            tk.Label(scrollable_frame, text="לא נמצאו מספרים באזור החיפוש", 
                    font=("Arial", 10)).pack(pady=20)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tab 2: Debug Information
        debug_frame = tk.Frame(notebook)
        notebook.add(debug_frame, text="מידע לאיתור בעיות")
        
        tk.Label(debug_frame, text="כל הטקסט האדום שנמצא באזור החיפוש:", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        debug_textbox = tk.Text(debug_frame, wrap=tk.WORD, height=15, font=("Courier New", 9))
        debug_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        if all_red_text:
            for i, span in enumerate(all_red_text):
                color_int = span["color"]
                r = (color_int >> 16) & 0xFF
                g = (color_int >> 8) & 0xFF
                b = color_int & 0xFF
                
                debug_textbox.insert(tk.END, f"{i+1}. טקסט: '{span['text']}'\n")
                debug_textbox.insert(tk.END, f"   צבע RGB: ({r}, {g}, {b})\n")
                debug_textbox.insert(tk.END, f"   גודל פונט: {span['size']:.1f}\n")
                debug_textbox.insert(tk.END, f"   מיקום: ({span['bbox'][0]:.1f}, {span['bbox'][1]:.1f})\n")
                debug_textbox.insert(tk.END, "-" * 50 + "\n")
        else:
            debug_textbox.insert(tk.END, "לא נמצא טקסט אדום באזור החיפוש\n")
            debug_textbox.insert(tk.END, "אפשרויות:\n")
            debug_textbox.insert(tk.END, "1. המספר אינו בצבע אדום\n")
            debug_textbox.insert(tk.END, "2. המספר נמצא מחוץ לאזור החיפוש (30% גובה, 50% רוחב)\n")
            debug_textbox.insert(tk.END, "3. הקובץ הוא סרוק ודורש OCR\n")
        
        debug_textbox.config(state=tk.DISABLED)
        
        # Tab 3: Top-left text
        top_left_frame = tk.Frame(notebook)
        notebook.add(top_left_frame, text="טקסט מהאזור")
        
        tk.Label(top_left_frame, text=f"כל הטקסט מאזור החיפוש (30% גובה, 50% רוחב):", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        top_left_textbox = tk.Text(top_left_frame, wrap=tk.WORD, height=15, font=("Arial", 9))
        top_left_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        top_left_textbox.insert(tk.END, top_left_text if top_left_text else "לא נמצא טקסט")
        top_left_textbox.config(state=tk.DISABLED)
        
        # Tab 4: Full text
        full_frame = tk.Frame(notebook)
        notebook.add(full_frame, text="כל הטקסט בדף")
        
        tk.Label(full_frame, text="כל הטקסט מהדף הראשון:", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        full_textbox = tk.Text(full_frame, wrap=tk.WORD, height=15, font=("Arial", 9))
        full_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        full_textbox.insert(tk.END, full_text if full_text else "לא נמצא טקסט")
        full_textbox.config(state=tk.DISABLED)
        
        # Close button
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="סגור", command=dialog.destroy,
                 font=("Arial", 10), bg="#607D8B", fg="white",
                 padx=20, pady=5).pack()
        
        # Make dialog modal
        dialog.grab_set()
    
    def use_extracted_number(self, number, dialog):
        """Use the selected extracted number for renaming"""
        dialog.destroy()
        # Set the number in a quick rename dialog
        self.perform_quick_rename_with_number(number)
    
    def create_quick_rename_dialog(self):
        """Create a custom positioned dialog for quick rename"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("מספר בדיקה")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        
        # Position dialog near the rename buttons
        self.position_dialog_near_buttons(dialog)
          
        # Create content
        tk.Label(dialog, text="הזן מספר בדיקה להוספה לתחילת שם הקובץ:", 
                font=("Arial", 10)).pack(pady=10, padx=20)
        
        entry_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=entry_var, font=("Arial", 12), width=20)
        entry.pack(pady=10, padx=20)
        entry.focus_set()
        
        result = [None]  # Use list to store result from nested functions
        
        def on_ok():
            result[0] = entry_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="אישור", command=on_ok, 
                 font=("Arial", 10), bg="#4CAF50", fg="white", 
                 padx=25, pady=2).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(button_frame, text="ביטול", command=on_cancel, 
                 font=("Arial", 10), bg="#f44336", fg="white", 
                 padx=25, pady=2).pack(side=tk.RIGHT, padx=2)
        
        # Bind Enter key to OK
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # Make dialog modal
        dialog.grab_set()
        self.root.wait_window(dialog)
        
        return result[0]
    
    def create_standard_rename_dialog(self, current_name):
        """Create a custom positioned dialog for standard rename"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("שינוי שם קובץ")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        
        # Position dialog near the rename buttons
        self.position_dialog_near_buttons(dialog)
        
        # Create content
        tk.Label(dialog, text="הזן שם חדש לקובץ (ללא סיומת .pdf):", 
                font=("Arial", 10)).pack(pady=10, padx=20)
        
        entry_var = tk.StringVar(value=current_name)
        entry = tk.Entry(dialog, textvariable=entry_var, font=("Arial", 12), width=25)
        entry.pack(pady=10, padx=20)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        result = [None]  # Use list to store result from nested functions
        
        def on_ok():
            result[0] = entry_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="אישור", command=on_ok, 
                 font=("Arial", 12), bg="#4CAF50", fg="white", 
                 padx=25, pady=2).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(button_frame, text="ביטול", command=on_cancel, 
                 font=("Arial", 12), bg="#f44336", fg="white", 
                 padx=25, pady=2).pack(side=tk.RIGHT, padx=2)
        
        # Bind Enter key to OK
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # Make dialog modal
        dialog.grab_set()
        self.root.wait_window(dialog)
        
        return result[0]
    
    def position_dialog_near_buttons(self, dialog, width=None, height=None):
        """Position dialog near the rename buttons in the right panel"""
        # Use provided dimensions or defaults for small dialogs
        dialog_width = width if width is not None else 350
        dialog_height = height if height is not None else 180
        
        # Get the position of the rename buttons frame
        button_frame = None
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.PanedWindow):
                for child in widget.winfo_children():
                    if hasattr(child, 'winfo_children'):
                        for subchild in child.winfo_children():
                            if isinstance(subchild, tk.Frame) and len(subchild.winfo_children()) > 0:
                                # Check if this frame contains rename buttons
                                for btn in subchild.winfo_children():
                                    if isinstance(btn, tk.Button) and "שינוי שם" in btn.cget('text'):
                                        button_frame = subchild
                                        break
                                if button_frame:
                                    break
                    if button_frame:
                        break
            if button_frame:
                break
        
        if button_frame:
            # Get button frame position relative to screen
            x = button_frame.winfo_rootx()
            y = button_frame.winfo_rooty()
            
            # Calculate position to avoid covering important content
            dialog_x = x + 50  # Offset to the right of buttons
            dialog_y = y - dialog_height - 20  # Position above buttons
            
            # Ensure dialog stays on screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if dialog_x + dialog_width > screen_width:
                dialog_x = screen_width - dialog_width - 20
            if dialog_y < 0:
                dialog_y = 20
            if dialog_y + dialog_height > screen_height:
                dialog_y = screen_height - dialog_height - 20
            
            dialog.geometry(f"{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}")
        else:
            # Fallback: center on screen
            dialog.geometry(f"{dialog_width}x{dialog_height}")
            dialog.eval(f'tk::PlaceWindow {dialog._w} center')
    
    def standard_rename(self):
        """Standard rename with full control"""
        if not self.selected_pdf:
            messagebox.showwarning("לא נבחר קובץ", 
                                  "אנא בחר קובץ PDF תחילה.",
                                  parent=self.root)
            return
        
        current_name = self.selected_pdf.stem  # Filename without extension
        
        # Use custom positioned dialog
        new_name = self.create_standard_rename_dialog(current_name)
        
        if not new_name:
            return  # User cancelled
        
        # Clean the filename (remove invalid characters)
        invalid_chars = '<>:"/\\|?*'
        new_name = "".join(c for c in new_name if c not in invalid_chars)
        
        if not new_name:
            messagebox.showerror("קלט לא תקין", 
                               "שם הקובץ לא יכול להיות רק תווים מיוחדים.",
                               parent=self.root)
            return
        
        # Add .pdf extension
        new_name = f"{new_name}.pdf"
        new_path = self.selected_pdf.parent / new_name
        
        # Check if trying to rename to same name
        if new_path == self.selected_pdf:
            messagebox.showinfo("אין שינוי", "שם הקובץ לא השתנה.",
                              parent=self.root)
            return
        
        # Check if file already exists
        if new_path.exists():
            if not messagebox.askyesno("הקובץ קיים", 
                                      f"קובץ בשם '{new_name}' כבר קיים.\nלהחליף אותו?",
                                      parent=self.root):
                return
        
        try:
            # Rename the file
            self.selected_pdf.rename(new_path)
            
            # Update internal state
            self.selected_pdf = new_path
            
            # Reload file list without clearing preview
            self.load_pdf_files(clear_preview=False)
            
            # Reselect the renamed file
            new_index = self.pdf_files.index(self.selected_pdf)
            self.pdf_listbox.selection_clear(0, tk.END)
            self.pdf_listbox.selection_set(new_index)
            self.pdf_listbox.see(new_index)
            
            # Update filename display and refresh preview
            self.filename_label.config(text=self.selected_pdf.name)
            self.preview_pdf()  # Refresh the preview
            
            messagebox.showinfo("הצלחה", f"שם הקובץ שונה ל:\n{new_name}",
                              parent=self.root)
            
        except Exception as e:
            messagebox.showerror("שגיאה בשינוי שם", 
                               f"לא ניתן לשנות את שם הקובץ:\n{str(e)}",
                               parent=self.root)


def main():
    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
