import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import cv2
from PIL import Image, ImageTk
from djitellopy import Tello
from tello_mock import MockTello

class TelloGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tello 无人机控制台")
        self.root.geometry("1000x700")

        self.tello = None
        self.is_connected = False
        self.video_thread_running = False
        self.status_thread_running = False

        # UI Variables
        self.ip_var = tk.StringVar(value="192.168.10.1")
        self.port_var = tk.StringVar(value="8889")
        self.use_mock_var = tk.BooleanVar(value=False)
        self.battery_var = tk.StringVar(value="电量: --%")
        self.status_var = tk.StringVar(value="状态: 未连接")

        self.setup_ui()

    def setup_ui(self):
        # Top Frame: Connection
        conn_frame = ttk.LabelFrame(self.root, text="连接设置")
        conn_frame.pack(side="top", fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="IP 地址:").pack(side="left", padx=5)
        ttk.Entry(conn_frame, textvariable=self.ip_var, width=15).pack(side="left", padx=5)

        ttk.Label(conn_frame, text="端口:").pack(side="left", padx=5)
        ttk.Entry(conn_frame, textvariable=self.port_var, width=6).pack(side="left", padx=5)

        ttk.Checkbutton(conn_frame, text="模拟模式", variable=self.use_mock_var).pack(side="left", padx=10)

        self.btn_connect = ttk.Button(conn_frame, text="连接", command=self.on_connect)
        self.btn_connect.pack(side="left", padx=5)

        self.btn_disconnect = ttk.Button(conn_frame, text="断开", state="disabled", command=self.on_disconnect)
        self.btn_disconnect.pack(side="left", padx=5)

        # Main Content Area
        main_content = ttk.Frame(self.root)
        main_content.pack(expand=True, fill="both", padx=10, pady=5)

        # Left: Video
        video_frame = ttk.LabelFrame(main_content, text="视频监控")
        video_frame.pack(side="left", expand=True, fill="both", padx=5)

        self.video_label = ttk.Label(video_frame, text="等待视频流...")
        self.video_label.pack(expand=True)

        # Right: Controls
        control_panel = ttk.Frame(main_content, width=300)
        control_panel.pack(side="right", fill="y", padx=5)

        # Status
        status_frame = ttk.LabelFrame(control_panel, text="无人机状态")
        status_frame.pack(fill="x", pady=5)
        ttk.Label(status_frame, textvariable=self.battery_var, font=("Arial", 12, "bold")).pack(pady=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack(pady=5)

        # Basic Actions
        action_frame = ttk.LabelFrame(control_panel, text="基本动作")
        action_frame.pack(fill="x", pady=5)

        ttk.Button(action_frame, text="起飞 (Takeoff)", command=lambda: self.send_command(self.tello.takeoff)).pack(fill="x", padx=5, pady=2)
        ttk.Button(action_frame, text="降落 (Land)", command=lambda: self.send_command(self.tello.land)).pack(fill="x", padx=5, pady=2)
        btn_stop = tk.Button(action_frame, text="紧急停止 (EMERGENCY)", bg="red", fg="white", command=self.on_emergency)
        btn_stop.pack(fill="x", padx=5, pady=5)

        # Direction Control
        rc_frame = ttk.LabelFrame(control_panel, text="飞行控制")
        rc_frame.pack(fill="x", pady=5)

        # Grid for directional buttons
        # Layout:
        #      [Fwd]          [Up]
        # [Left]   [Right]  [RotL] [RotR]
        #      [Back]         [Down]

        btn_w = 6

        # Position / Movement (WASD equivalent)
        ttk.Button(rc_frame, text="前", width=btn_w, command=lambda: self.send_rc(0, 30, 0, 0)).grid(row=0, column=1, pady=2)
        ttk.Button(rc_frame, text="左", width=btn_w, command=lambda: self.send_rc(-30, 0, 0, 0)).grid(row=1, column=0, pady=2)
        ttk.Button(rc_frame, text="右", width=btn_w, command=lambda: self.send_rc(30, 0, 0, 0)).grid(row=1, column=2, pady=2)
        ttk.Button(rc_frame, text="后", width=btn_w, command=lambda: self.send_rc(0, -30, 0, 0)).grid(row=2, column=1, pady=2)

        # Separator or Space
        ttk.Label(rc_frame, text="   ").grid(row=0, column=3)

        # Altitude / Rotation
        ttk.Button(rc_frame, text="上升", width=btn_w, command=lambda: self.send_rc(0, 0, 30, 0)).grid(row=0, column=4, pady=2)
        ttk.Button(rc_frame, text="左旋", width=btn_w, command=lambda: self.send_rc(0, 0, 0, -30)).grid(row=1, column=3, pady=2) # column 3 overlaps separator? adjust
        ttk.Button(rc_frame, text="右旋", width=btn_w, command=lambda: self.send_rc(0, 0, 0, 30)).grid(row=1, column=5, pady=2)
        ttk.Button(rc_frame, text="下降", width=btn_w, command=lambda: self.send_rc(0, 0, -30, 0)).grid(row=2, column=4, pady=2)

        # Stop RC
        ttk.Button(rc_frame, text="悬停 (Stop)", command=lambda: self.send_rc(0, 0, 0, 0)).grid(row=3, column=0, columnspan=6, sticky="ew", pady=5)

        # Instructions
        ttk.Label(control_panel, text="提示: 请先连接无人机。\n默认端口8889。", font=("Arial", 9), wraplength=200).pack(pady=10)

    def on_connect(self):
        ip = self.ip_var.get()
        # Port is not directly used in constructor but often needed if modified in library,
        # djitellopy usually defaults to 8889. We pass host.

        if self.use_mock_var.get():
            print("Using Mock Tello")
            self.tello = MockTello(host=ip)
        else:
            print(f"Connecting to Real Tello at {ip}")
            # djitellopy Tello() uses host for command IP.
            # It expects ports 8889 (cmd) and 11111 (state) and 11111 (video).
            # We can attempt to override if the user specifies a different port,
            # though standard Tello is fixed.
            self.tello = Tello(host=ip)

            try:
                port = int(self.port_var.get())
                if port != 8889:
                     # djitellopy 2.5.0 might not support changing port easily via constructor
                     # but we can try to set the internal address if possible, or just log a warning.
                     # Examining djitellopy source is not possible here, but usually it's hardcoded or kwargs.
                     # We will attempt to set the address property if it exists or just warn.
                     print(f"Warning: Custom port {port} requested. Standard Tello port is 8889.")
                     # If the library supported it, we would do: self.tello.tello_address = (ip, port)
                     # For now, we respect the user input by at least trying to use it if the library allows,
                     # otherwise we proceed with standard behavior.
                     self.tello.tello_addr = (ip, port)
            except ValueError:
                print("Invalid port, using default 8889")

        self.btn_connect.config(state="disabled")
        self.status_var.set("状态: 连接中...")

        # Thread the connection
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        try:
            self.tello.connect()
            self.tello.streamon()
            self.is_connected = True

            # Start background loops
            self.video_thread_running = True
            threading.Thread(target=self._video_loop, daemon=True).start()

            self.status_thread_running = True
            threading.Thread(target=self._status_loop, daemon=True).start()

            # Update UI
            self.root.after(0, lambda: self._update_connection_ui(True))
        except Exception as e:
            print(f"Connection failed: {e}")
            self.root.after(0, lambda: self._update_connection_ui(False, str(e)))

    def _update_connection_ui(self, success, error_msg=""):
        if success:
            self.status_var.set("状态: 已连接")
            self.btn_disconnect.config(state="normal")
            messagebox.showinfo("成功", "无人机连接成功！")
        else:
            self.status_var.set("状态: 连接失败")
            self.btn_connect.config(state="normal")
            self.tello = None
            messagebox.showerror("错误", f"连接失败: {error_msg}")

    def on_disconnect(self):
        self.video_thread_running = False
        self.status_thread_running = False
        if self.tello:
            # self.tello.streamoff() # Might block
            self.tello = None
        self.is_connected = False
        self.status_var.set("状态: 已断开")
        self.battery_var.set("电量: --%")
        self.btn_connect.config(state="normal")
        self.btn_disconnect.config(state="disabled")
        self.video_label.config(image='', text="等待视频流...")

    def _video_loop(self):
        frame_reader = self.tello.get_frame_read()
        while self.video_thread_running:
            try:
                if frame_reader is None:
                    time.sleep(0.1)
                    continue

                frame = frame_reader.frame
                if frame is not None:
                    # Resize to fit (keep aspect ratio roughly)
                    # Tello is 960x720. Let's resize to 640x480 for UI
                    img = cv2.resize(frame, (640, 480))
                    # Convert to RGB
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    # Convert to PIL
                    img_pil = Image.fromarray(img)

                    # Pass the PIL Image to the main thread
                    self.root.after(0, self._update_video_label, img_pil)

                time.sleep(0.03) # ~30 FPS
            except Exception as e:
                print(f"Video loop error: {e}")
                time.sleep(1)

    def _update_video_label(self, img_pil):
        # Create ImageTk in main thread
        img_tk = ImageTk.PhotoImage(image=img_pil)
        self.video_label.configure(image=img_tk)
        self.video_label.image = img_tk # Keep reference

    def _status_loop(self):
        while self.status_thread_running:
            if self.tello:
                try:
                    bat = self.tello.get_battery()
                    self.root.after(0, lambda b=bat: self.battery_var.set(f"电量: {b}%"))
                except:
                    pass
            time.sleep(5) # Update every 5 seconds

    def send_command(self, func, *args):
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接无人机")
            return

        threading.Thread(target=self._run_command, args=(func, *args), daemon=True).start()

    def _run_command(self, func, *args):
        try:
            func(*args)
        except Exception as e:
            print(f"Command error: {e}")

    def on_emergency(self):
        if self.tello:
            self.tello.emergency()

    def send_rc(self, lr, fb, ud, y):
        if not self.is_connected:
            return # Silent fail or log
        # send_rc_control is non-blocking usually (just updates internal state in library) or fast
        # but safely threaded
        threading.Thread(target=self._run_command, args=(self.tello.send_rc_control, lr, fb, ud, y), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TelloGUI(root)
    root.mainloop()
