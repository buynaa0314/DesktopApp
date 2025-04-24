import cv2
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np
import datetime
import json
import os
from ultralytics import YOLO

video_path = "C:/Users/ThinkPad/Downloads/parking1(2).mp4"
cap = cv2.VideoCapture(video_path)

model = YOLO('yolov8l.pt')  

spots = []
detected_spots = []
current_color = (0, 255, 0)

# ------- GUI -------
root = tk.Tk()
root.title("🚗Ширээний аппликейшн ")
root.geometry("950x750")

settings_frame = tk.LabelFrame(root, text="⚙️ Settings", font=("Arial", 9), padx=5, pady=5)
settings_frame.place(x=10, y=10)

tk.Label(settings_frame, text="Камер IP:", font=("Arial", 8)).grid(row=0, column=0, sticky='w')
camera_ip_entry = tk.Entry(settings_frame, width=15)
camera_ip_entry.grid(row=0, column=1, pady=2)

tk.Label(settings_frame, text="localhost:", font=("Arial", 8)).grid(row=1, column=0, sticky='w')
server_ip_entry = tk.Entry(settings_frame, width=15)
server_ip_entry.grid(row=1, column=1, pady=2)

def set_green():
    global current_color
    current_color = (0, 255, 0)

def set_red():
    global current_color
    current_color = (0, 0, 255)

tk.Label(settings_frame, text="Зогсоолын төрөл:", font=("Arial", 8)).grid(row=2, column=0, sticky='w')
tk.Button(settings_frame, text="Сул", bg="green", command=set_green, width=10).grid(row=2, column=1, pady=1)
tk.Button(settings_frame, text="Машинтай", bg="red", command=set_red, width=10).grid(row=3, column=1, pady=1)

def save_spots():
    data = [{
        'x1': x1, 'y1': y1,
        'x2': x2, 'y2': y2,
        'color': list(color)  # өнгийг list болгон хадгалж байна
    } for ((x1, y1), (x2, y2), color) in spots]
    with open("spots.json", "w") as f:
        json.dump(data, f)
    print("✅ Зогсоолууд хадгалагдлаа")

def clear_spots():
    global spots, detected_spots
    spots = []
    detected_spots = []
    print("🗑️ Зогсоолууд устгагдлаа")

tk.Button(settings_frame, text="💾 Хадгалах", command=save_spots, width=10).grid(row=4, column=1, pady=2)
tk.Button(settings_frame, text="🗑️ Устгах", command=clear_spots, width=10).grid(row=5, column=1, pady=2)

def browse_video():
    global cap
    file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov")])
    if file_path:
        cap.release()
        cap = cv2.VideoCapture(file_path)
        print("✅ Бичлэг сонгогдлоо:", file_path)

tk.Label(settings_frame, text="Бичлэг:", font=("Arial", 8)).grid(row=6, column=0, sticky='w')
tk.Button(settings_frame, text="📁 Browse", command=browse_video, width=10).grid(row=6, column=1, pady=3)

canvas = tk.Canvas(root, width=640, height=480, bg='black')
canvas.place(x=250, y=50)

# Төлөвийн Label-үүд
detected_label = tk.Label(root, text="🟦 Илэрсэн машин: 0", font=("Arial", 10))
detected_label.place(x=250, y=540)

free_label = tk.Label(root, text="🟩 Сул зогсоол: 0", font=("Arial", 10))
free_label.place(x=450, y=540)

occupied_label = tk.Label(root, text="🟥 Машинтай зогсоол: 0", font=("Arial", 10))
occupied_label.place(x=250, y=570)

time_label = tk.Label(root, text="⏰ Цаг: ", font=("Arial", 10))
time_label.place(x=450, y=570)

start_x = start_y = 0
rect = None

def on_mouse_down(event):
    global start_x, start_y, rect
    start_x, start_y = event.x, event.y
    rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="green")

def on_mouse_move(event):
    if rect:
        canvas.coords(rect, start_x, start_y, event.x, event.y)

def on_mouse_up(event):
    global rect
    x1, y1, x2, y2 = canvas.coords(rect)
    x1, x2 = sorted([int(x1), int(x2)])
    y1, y2 = sorted([int(y1), int(y2)])
    color = current_color
    spots.append(((x1, y1), (x2, y2), color))
    detected_spots.append(False if color == (0, 255, 0) else True)  # машинтай болсноор False хадгалах
    rect = None

canvas.bind("<ButtonPress-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_move)
canvas.bind("<ButtonRelease-1>", on_mouse_up)

def show_spots(total_cars):
    total = len(spots)
    free = sum(1 for s in detected_spots if s is False)  # False => машингүй (сул)
    busy = total - free
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    detected_label.config(text=f"🟦 Илэрсэн машин: {total_cars}")
    free_label.config(text=f"🟩 Сул зогсоол: {free}")
    occupied_label.config(text=f"🟥 Машинтай зогсоол: {busy}")
    time_label.config(text=f"⏰ Цаг: {time_str}")

def is_car_in_spot(spot_rect, car_boxes):
    x1, y1 = spot_rect[0]
    x2, y2 = spot_rect[1]
    spot_box = [x1, y1, x2, y2]
    for box in car_boxes:
        bx1, by1, bx2, by2 = box
        if not (bx2 < x1 or bx1 > x2 or by2 < y1 or by1 > y2):
            return True
    return False

def update_video():
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return

    frame = cv2.resize(frame, (640, 480))
    results = model.predict(source=frame, conf=0.4, classes=[2])
    car_boxes = []

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            car_boxes.append([x1, y1, x2, y2])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)

    new_detected = []
    for idx, ((x1, y1), (x2, y2), _) in enumerate(spots):
        occupied = is_car_in_spot(((x1, y1), (x2, y2)), car_boxes)
        color = (0, 0, 255) if occupied else (0, 255, 0)

        # өнгийг шинэчилж хадгалах
        spots[idx] = ((x1, y1), (x2, y2), color)

        new_detected.append(occupied)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    detected_spots[:] = new_detected
    show_spots(len(car_boxes))

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    imgtk = ImageTk.PhotoImage(image=img)
    canvas.imgtk = imgtk
    canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)

    root.after(30, update_video)

def load_saved_spots():
    global spots, detected_spots
    if os.path.exists("spots.json"):
        with open("spots.json", "r") as f:
            data = json.load(f)
            for item in data:
                x1, y1 = item["x1"], item["y1"]
                x2, y2 = item["x2"], item["y2"]
                color = tuple(item["color"])
                spots.append(((x1, y1), (x2, y2), color))
                detected_spots.append(False if color == (0, 255, 0) else True)

load_saved_spots()
update_video()
root.mainloop()
cap.release()
cv2.destroyAllWindows()
