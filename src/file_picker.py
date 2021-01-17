import re
import random
from glob import glob
from pathlib import Path
from copy import copy

import tkinter as tk
from tkinter.filedialog import askopenfilename


class FilePicker(tk.Frame):
    def __init__(
            self,
            *args,
            callback=None,
            settings=None,
            **kwargs):
        super().__init__(*args, **kwargs)
        self.pack()
        self.pattern = re.compile('$|^[1-9][0-9]*')
        self.old_settings = settings
        self.settings = copy(settings)
        self.image_path = self.settings.image_path
        self.image_label = self.settings.image_path
        self.num_pieces = tk.IntVar(value=self.settings.num_pieces)
        self.piece_rotation = tk.BooleanVar(value=self.settings.piece_rotation)
        self.create_widgets()
        self.callback = callback

    def create_widgets(self):
        tk.Button(
            self,
            text='Select Image',
            command=self.select_image
        ).pack()
        tk.Button(
            self,
            text='Random',
            command=self.random
        ).pack()
        self.image_label = tk.Label(text=self.image_path)
        self.image_label.pack()

        command = self.register(self.validate_entry)
        tk.Entry(
            self,
            textvariable=self.num_pieces,
            validate='key',
            validatecommand=(command, '%P')
        ).pack()

        tk.Checkbutton(
            self,
            text='Piece rotation',
            variable=self.piece_rotation
        ).pack()

        tk.Button(self, text='Done', command=self.done).pack()

        tk.Button(
            self,
            text='Cancel',
            fg='red',
            command=self.master.destroy
        ).pack()

    def select_image(self):
        self.image_path = askopenfilename(
            filetypes=[('*', 'jpg'), ('*', 'jpeg'), ('*', 'png')],
            initialdir=' '  # This will remember the previously used path
        )
        self.image_label['text'] = self.image_path

    def random(self):
        random_folder = Path(self.image_path).parent
        files = []
        for filetype in ['jpg', 'jpeg', 'png']:
            files.extend(glob(f"{random_folder}/*.{filetype}"))

        if len(files) > 0:
            index = random.randrange(0, len(files))
            self.image_path = files[index]
            self.image_label['text'] = self.image_path

    def done(self):
        self.settings.num_intended_pieces = self.num_pieces.get()
        self.settings.image_path = self.image_path
        self.settings.piece_rotation = self.piece_rotation.get()
        self.callback(self.settings)
        self.master.destroy()

    def validate_entry(self, entry):
        return self.pattern.fullmatch(entry) is not None


def select_image(callback, settings):
    root = tk.Tk()
    app = FilePicker(
        master=root,
        callback=callback,
        settings=settings
        # image_path=image_path,
        # intended_pieces=intended_pieces,
        # snap_distance_percent=snap_distance_percent,
        # piece_rotation=piece_rotation
    )
    root.geometry('500x300')
    app.mainloop()
