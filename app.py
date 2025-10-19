import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import os


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
    
    def position_dialog_near_buttons(self, dialog):
        """Position dialog near the rename buttons in the right panel"""
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
            
            # Position dialog above the buttons with some offset
            dialog_width = 350
            dialog_height = 180
            
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
            dialog.geometry("350x180")
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
