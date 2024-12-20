import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image
import os
from datetime import datetime
from exif_labels import exif_labels_dict
from scorpion import image_extensions, get_metadata, check_extension


class MetadataViewerApp:
    def __init__(self, root, width, height):
        self.root = root
        self.root.title("Metadata Viewer")
        self.root.geometry(f"{width}x{height}")  # Set the window size

        # Setup GUI layout
        self.create_widgets()

    def create_widgets(self):
        # Buttons for file and folder selection
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

        tk.Button(btn_frame, text="Open Files", command=self.open_files).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Open Folders", command=self.open_dirs).pack(side=tk.LEFT, padx=5)

        # Treeview for displaying metadata
        self.tree = ttk.Treeview(self.root, columns=("Tag", "Value"), show="headings")
        self.tree.heading("Tag", text="Tag")
        self.tree.heading("Value", text="Value")
        self.tree.pack(fill=tk.BOTH, expand=True)

    def open_files(self) -> None:
        """
        Forge the string of the handled extensions.
        This is needed by 'filedialog.askopenfilename',
        and the format is: "*.jpg *.jpg *.png" 
        """
        extensions = ""
        ext_len = len(image_extensions) - 1
        for i, ext in enumerate(image_extensions):
            extensions += '*' + ext
            if i < ext_len:
                extensions += " "

        # Set the filetypes argument for the askopenfilename() method
        filetypes = (
            ('Image files', extensions),
        )

        # Open the dialog to select the file names
        file_paths = filedialog.askopenfilename(
            title="Select image files",
            filetypes=filetypes,  # Send the handled file types
            multiple=True  # Activate multiple selection
        )

        self.read_metadata_from_files(file_paths)

    def read_metadata_from_files(self, files: list[str]) -> None:
        for path in files:
            if not check_extension(path):
                continue
            try:
                if os.path.isfile(path):
                    metadata = get_metadata(path)
                    self.display_metadata(metadata)
            except Exception as e:
                messagebox.showerror("Error", f"Could not read metadata: {e}")

    def open_dirs(self):
        dir_path = filedialog.askdirectory(title="Select folders")

        if dir_path:
            files = [
                os.path.join(dir_path, filename)
                for filename in os.listdir(dir_path)
            ]
            # Read the metadata of each file in the folder
            if files:
                self.read_metadata_from_files(files)

    def display_metadata(self, metadata: dict[str]) -> None:
        try:
            if metadata:
                for tag, value in metadata.items():
                    self.tree.insert("", tk.END, values=(tag, value))
            else:
                messagebox.showinfo("Metadata Viewer", "No metadata found.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not read metadata: {e}")
        self.tree.insert("", tk.END, values=("", ""))

if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataViewerApp(root, 600, 600)
    root.mainloop()
