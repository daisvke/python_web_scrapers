#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, PngImagePlugin
import piexif
import os
from datetime import datetime
from exif_labels import exif_labels_dict
from scorpion import get_metadata, check_extension
from sys import stderr
from typing import Any, Tuple
from config import *
from fractions import Fraction
import struct


class MetadataViewerApp:
    def __init__(self, root, width, height):
        self.root = root
        self.root.title("Metadata Viewer")
        self.root.geometry(f"{width}x{height}")  # Set the window size
        # Mapping of Treeview item IDs to filenames
        self.item_to_file = {}

        # Setup GUI layout
        self.create_widgets()

    def create_widgets(self) -> None:
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

        # Double-click binding for editing the value fields
        self.tree.bind("<Double-1>", self.on_double_click)
        # Del key binding for deleting metadata entries
        self.tree.bind("<Delete>", self.delete_selected_entry)

    def open_files(self) -> None:
        """
        Open all the selected files to extract metadata from.
        """
        
        """
        Forge the string of the handled extensions.
        This is needed by 'filedialog.askopenfilename',
        and the format is: "*.jpeg *.jpg *.png" 
        """
        extensions = ""
        ext_len = len(IMAGE_EXTENSIONS) - 1
        for i, ext in enumerate(IMAGE_EXTENSIONS):
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

    def read_metadata_from_files(self, files: str|list[str]) -> None:
        """
        Read and display all metadata from each provided files.
        """
        for path in files:
             # If file extension isn't handled or path isn't a valid file
            if not check_extension(path) or not os.path.isfile(path):
                continue
            try:
                metadata = get_metadata(path)
                self.display_metadata(path, metadata)
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

    def display_metadata(self, file_path: str, metadata: dict[str,str]) -> None:
        """
        Display metadata of the image.
        Keep useful data as 'tags' in the tree items.
        """

        try:
            if not metadata:
                raise ValueError(f"Could not read metadata from {file_path}")

            basic, png, exif = metadata[BASIC], metadata[PNG], metadata[EXIF]

            if basic:
                for tag, value in basic.items():
                    item_id = self.tree.insert(
                        "", tk.END, values=(tag, value), tags=(file_path, (BASIC,))
                    )
            if png:
                for tag, value in png.items():
                    item_id = self.tree.insert(
                        "", tk.END, values=(tag, value), tags=(file_path, (PNG,))
                    )
            elif exif:
                for tag, value in exif.items():
                    human_readable_tag = value[0]

                    item_id = self.tree.insert(
                        "",
                        tk.END,
                        values=(human_readable_tag, value[1]),
                        tags=(file_path, (EXIF, tag))
                    )
        except Exception as e:
            messagebox.showerror("Error", e)
        self.tree.insert("", tk.END, values=("", ""))

    # def check_if_data_is_editable(self, item_id: str) -> Tuple[Any,Any]:
    #     """
    #     Check if the data is not Exif data, as we will
    #     not edit them.
    #     """
    #     # Get the current tag/value in a tuple 
    #     values = self.tree.item(item_id, "values")
    #     if not values:
    #         return (False, False)

    #     # Get the tag to check if they are Exif data
    #     if len(values) == 2:
    #         tag = values[0]
    #         value = values[1]
    #     else:
    #         return (False, False)

    #     if tag in not_exif:
    #         return (False, False)
    #     return (tag, value)

    def delete_selected_entry(self, event) -> None:
        """
        Deletes the currently selected metadata entry when the
        Delete key is pressed.
        """
        # Get the selected item
        selected_item = self.tree.selection()
        if selected_item:
            # Remove the selected item from the Treeview
            for item_id in selected_item:
                tag, value = self.tree.item(item_id, "values")
                tags = self.tree.item(item_id, "tags")
                if not tag or not value:
                    continue

                # First, delete the metadata entry from the file
                # Get the file associated with the item
                file_path = tags[FILEPATH]

                if not file_path:
                    continue

                self.modify_and_save_metadata_to_file(file_path, tag, tags)

                # Then, delete the data from the tree
                self.tree.delete(item_id)

    def on_double_click(self, event) -> None:
        """Handles double-clicking a value in the Treeview to edit it."""
        # Identify the selected item and column
        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)

        if column_id != "#2":  # Only allow editing the "Value" column
            return

        tag, value = self.tree.item(item_id, "values")
        tags = self.tree.item(item_id, "tags")
        if not tag or not value:
            return

        # Create an entry widget for editing
        entry = tk.Entry(self.tree)
        entry.insert(0, value)
        entry.focus()

        # Place the entry widget over the cell
        bbox = self.tree.bbox(item_id, column_id)
        entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])

        # Commit the new value when the entry loses focus or Enter is pressed
        def save_edit(event=None):
            new_value = entry.get()

            # Get the file associated with the item
            file_path = tags[FILEPATH]
            if not file_path:
                return
            # Update the data on the file
            self.modify_and_save_metadata_to_file(
                file_path, tag, tags, new_value
                )
            # Update the data on the tree
            self.tree.item(item_id, values=(tag, new_value))
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    def convert_value_to_metadata_type(self, value: any, metadata_type: int) -> any:
        """
        Convert a value to the specified metadata type.

        This function handles various data types commonly used in metadata formats, 
        including EXIF, PNG `img.info`, and other image metadata formats.

        Parameters:
            value: The value to convert.
            metadata_type: An integer representing the metadata type (e.g., EXIF types).

        Returns:
            The value converted to the specified metadata type.

        Raises:
            ValueError: If the metadata type is unsupported.

        Notes on floats:
            Float numbers are stored as rationals in all regular metadata entries.
        
            EXIF metadata is meant to be universally compatible across devices and platforms,
            many of which historically lacked robust support for floating-point arithmetic.
            Rational types, which represent values as integers, ensure broader compatibility.
            This is why float values are stored as rationals.
            The float type also exists for later compatibility and custom metadata.

            Computers store floating-point numbers as approximations using a binary format
            (IEEE 754 standard). For instance, 72.1 cannot be represented precisely as a
            binary floating-point number. Instead, it is stored as the closest approximation,
            which is 72.0999984741211.

            This is why we are rounding the float value before sending back the converted
            float value.
        """
        print(f"METTAAAA: {metadata_type}, value: {value}")
        if metadata_type == 1:  # Byte
            return int(value) & 0xFF  # Ensure within 0-255
        elif metadata_type == 2:  # ASCII
            return str(value) + '\0'  # Null-terminated string
        elif metadata_type == 3:  # Short
            return int(value) & 0xFFFF  # Ensure within 0-65535
        elif metadata_type == 4:  # Long
            return int(value) & 0xFFFFFFFF  # Ensure within 0-4294967295
        elif metadata_type == 5:  # Rational
            value = struct.unpack('f', struct.pack('f', float(value)))[0]
            return  round(value, 1)
        elif metadata_type == 6:  # SByte
            return int(value) if -128 <= int(value) <= 127 else None
        elif metadata_type == 7:  # Undefined
            return bytes(value, "utf-8") if isinstance(value, str) else bytes(value)
        elif metadata_type == 8:  # SShort
            return int(value) if -32768 <= int(value) <= 32767 else None
        elif metadata_type == 9:  # SLong
            return int(value) if -2147483648 <= int(value) <= 2147483647 else None
        elif metadata_type == 10:  # SRational
            fraction = Fraction(float(value)).limit_denominator(10000)
            return (fraction.numerator, fraction.denominator)
        elif metadata_type == 11:  # Float
            return struct.unpack('f', struct.pack('f', float(value)))[0]
        elif metadata_type == 12:  # DFloat
            return struct.unpack('d', struct.pack('d', float(value)))[0]
        else:
            raise ValueError(f"Unsupported metadata type: {metadata_type}")

    def modify_and_save_metadata_to_file(
        self, file_path: str, tag_name: any, tags: any, value: any = "") -> bool:
        """
        Modify or remove a specific metadata tag from the image file.

        Args:
            file_path   : Path to the image file.
            tag_name    : The name of the tag to edit (e.g., "Model").
            tags        : Payload containing info about the item to edit
			value       : Needed in case of a modification

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            payload     = tags[PAYLOAD].split()
            datatype    = int(payload[DATATYPE])  # BASIC, PNG or EXIF
            img         = Image.open(file_path)   # Load the image and extract EXIF data
            print(f"tag nammmme: {tag_name} typrrrrr: {datatype} tags: {tags}")

            if datatype == EXIF:
                tag_id = int(payload[TAG_ID])  # int tag ID (and not human-readable tag name)
                print(f"tag iddddd:1111 {tag_id} type: {type(tag_id)}")

                exif_data = img.getexif()

                # If Exif data is present, we are updating it
                if exif_data and tag_id in exif_data:

                    # Detect type
                    tag_type = int(exif_labels_dict.get(tag_id, {}).get("type"))
                    print(f"tagtype: {tag_type}, value: {value}")
                    value = self.convert_value_to_metadata_type(value, tag_type)

                    # If a value is provided, it is a modification
                    if value:
                        print(f"Editing tag: {tag_name})")
                        exif_data[tag_id] = value
                    else:  # Otherwise, it is a deletion
                        print(f"Removing tag: {tag_name}")
                        del exif_data[tag_id]
                    
                    print(exif_data) # TODO delete
                    print(f"tag: {tag_name}, val: {value}")
                    exif_bytes = piexif.dump(exif_data)

                    # Save the modified metadata back to the file
                    img.save(file_path, exif=exif_data)

            elif datatype == PNG and img.format == "PNG" and img.info:
                img.save(file_path, pnginfo=img.info)

        except Exception as e:
            messagebox.showerror(
                "Error", f"Error while modifying the file data: {e}"
            )
            return False

        return True

if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataViewerApp(root, 600, 600)
    root.mainloop()
