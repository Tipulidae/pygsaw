import tkinter as tk
from tkinter.filedialog import askopenfilename


class FilePicker(tk.Frame):
    def __init__(self, *args, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pack()
        self.filename = 'None'
        self.image_label = None
        self.num_pieces = tk.IntVar(value=200)
        self.create_widgets()
        self.callback = callback

    def create_widgets(self):
        tk.Button(
            self,
            text='Select Image',
            command=self.select_image
        ).pack()
        self.image_label = tk.Label(text=self.filename)
        self.image_label.pack()
        tk.Entry(self, textvariable=self.num_pieces).pack()

        tk.Button(self, text='Done', command=self.done).pack()

        tk.Button(
            self,
            text='Cancel',
            fg='red',
            command=self.master.destroy
        ).pack()

    def select_image(self):
        self.filename = askopenfilename(
            filetypes=[('*', 'jpg'), ('*', 'png')]
        )
        self.image_label['text'] = self.filename

    def done(self):
        self.callback(
            self.filename,
            self.num_pieces.get()
        )
        self.master.destroy()


def select_image(callback):
    root = tk.Tk()
    app = FilePicker(master=root, callback=callback)
    root.geometry('500x300')
    app.mainloop()
