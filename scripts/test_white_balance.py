import sys
import tkinter as tk
from PIL import Image, ImageTk

# ==========================
# FILTER (UNCHANGED LOGIC)
# ==========================

def apply_filter(img,
                 grayscale=True,
                 wb_r=1.0,
                 wb_g=1.0,
                 wb_b=1.0,
                 contrast=1.0):
    img = img.convert("RGB")

    if grayscale:
        img = img.convert("L").convert("RGB")

    r, g, b = img.split()
    r = r.point(lambda i: min(255, int(i * wb_r)))
    g = g.point(lambda i: min(255, int(i * wb_g)))
    b = b.point(lambda i: min(255, int(i * wb_b)))
    img = Image.merge("RGB", (r, g, b))

    gray = img.convert("L")
    table = [
        max(0, min(255, int(128 + (i - 128) * contrast)))
        for i in range(256)
    ]
    gray = gray.point(table)

    return gray.convert("RGB")

# ==========================
# APP SETUP
# ==========================

# if len(sys.argv) < 2:
#     print("Usage: python script_b.py image.png")
#     sys.exit(1)

# original_image = Image.open(sys.argv[1])
original_image = Image.open(".\\working\\png-scans\\part-1\\temp\\IMSLP935307-PMLP1467582-farbigenoten1 27 of 27.png")

root = tk.Tk()
root.title("Filter Tester")
root.geometry("1000x600")

# ==========================
# STATE
# ==========================

grayscale_var = tk.BooleanVar(value=True)
contrast_var = tk.DoubleVar(value=1.0)

wb_r = tk.DoubleVar(value=1.0)
wb_g = tk.DoubleVar(value=1.0)
wb_b = tk.DoubleVar(value=1.0)


crop_box = None
drag_start = None

# ==========================
# LAYOUT
# ==========================

main = tk.Frame(root)
main.pack(fill="both", expand=True)

image_frame = tk.Frame(main)
image_frame.pack(side="left", fill="both", expand=True)

controls_frame = tk.Frame(main, width=280)
controls_frame.pack(side="right", fill="y")
controls_frame.pack_propagate(False)

canvas = tk.Canvas(image_frame, bg="black")
canvas.pack(fill="both", expand=True)

# ==========================
# IMAGE UPDATE
# ==========================

current_tk_image = None
display_rect = None

def update_image(*_):
    global current_tk_image

    img = original_image
    if crop_box:
        img = img.crop(crop_box)

    img = apply_filter(
        img,
        grayscale=grayscale_var.get(),
        wb_r=wb_r.get(),
        wb_g=wb_g.get(),
        wb_b=wb_b.get(),
        contrast=contrast_var.get()
    )


    canvas.update_idletasks()
    cw, ch = canvas.winfo_width(), canvas.winfo_height()

    # Prevent invalid canvas size
    if cw < 2 or ch < 2:
        return

    scale = min(cw / img.width, ch / img.height)

    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))

    img = img.resize((new_w, new_h))

    current_tk_image = ImageTk.PhotoImage(img)
    canvas.delete("all")
    canvas.create_image(cw // 2, ch // 2, image=current_tk_image, anchor="center")

# ==========================
# MOUSE SELECTION (ZOOM)
# ==========================

def on_mouse_down(event):
    global drag_start, display_rect
    drag_start = (event.x, event.y)
    display_rect = canvas.create_rectangle(
        event.x, event.y, event.x, event.y,
        outline="red"
    )

def on_mouse_drag(event):
    if drag_start and display_rect:
        canvas.coords(display_rect, drag_start[0], drag_start[1], event.x, event.y)

def on_mouse_up(event):
    global crop_box, drag_start, display_rect

    if not drag_start:
        return

    x1, y1 = drag_start
    x2, y2 = event.x, event.y
    canvas.delete(display_rect)

    if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
        drag_start = None
        return

    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    img = original_image

    scale = min(cw / img.width, ch / img.height)
    iw, ih = img.width * scale, img.height * scale
    ox, oy = (cw - iw) / 2, (ch - ih) / 2

    ix1 = int((min(x1, x2) - ox) / scale)
    iy1 = int((min(y1, y2) - oy) / scale)
    ix2 = int((max(x1, x2) - ox) / scale)
    iy2 = int((max(y1, y2) - oy) / scale)

    crop_box = (
        max(0, ix1),
        max(0, iy1),
        min(img.width, ix2),
        min(img.height, iy2),
    )

    drag_start = None
    update_image()

def reset_crop(_):
    global crop_box
    crop_box = None
    update_image()

canvas.bind("<ButtonPress-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_drag)
canvas.bind("<ButtonRelease-1>", on_mouse_up)
canvas.bind("<Button-3>", reset_crop)

# ==========================
# CONTROL HELPERS
# ==========================

def slider_with_entry(parent, label, var, min_val=0.5, max_val=2.0):
    tk.Label(parent, text=label).pack(anchor="w", pady=(10, 0))

    row = tk.Frame(parent)
    row.pack(fill="x")

    slider = tk.Scale(
        row,
        from_=min_val,
        to=max_val,
        resolution=0.01,
        orient="horizontal",
        variable=var,
        command=lambda _: update_image()
    )
    slider.pack(side="left", fill="x", expand=True)

    entry = tk.Entry(row, width=6)
    entry.pack(side="right", padx=5)
    entry.insert(0, f"{var.get():.2f}")

    def sync_from_entry(_):
        try:
            v = float(entry.get())
            var.set(max(min_val, min(max_val, v)))
            update_image()
        except ValueError:
            pass

    def sync_from_var(*_):
        entry.delete(0, tk.END)
        entry.insert(0, f"{var.get():.2f}")

    entry.bind("<Return>", sync_from_entry)
    var.trace_add("write", sync_from_var)

# ==========================
# CONTROLS
# ==========================

tk.Checkbutton(
    controls_frame,
    text="Grayscale",
    variable=grayscale_var,
    command=update_image
).pack(anchor="w", pady=5)

slider_with_entry(controls_frame, "White Balance – Red", wb_r)
slider_with_entry(controls_frame, "White Balance – Green", wb_g)
slider_with_entry(controls_frame, "White Balance – Blue", wb_b)

slider_with_entry(
    controls_frame,
    "Contrast",
    contrast_var,
    min_val=0.0,
    max_val=5.0
)

tk.Label(
    controls_frame,
    text="Drag to zoom • Right-click to reset",
    fg="gray"
).pack(anchor="w", pady=15)

# ==========================
# EVENTS
# ==========================

root.bind("<Configure>", lambda e: update_image())

update_image()
root.mainloop()
