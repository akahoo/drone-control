import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import cv2
import queue
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

        # Command Queue
        self.command_queue = queue.Queue()
        self.queue_thread_running = True
        self.is_executing_blocking_cmd = False # Flag for UI locking
        threading.Thread(target=self._command_worker, daemon=True).start()

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

        # We store buttons in list to easily disable/enable
        self.action_buttons = []

        btn_takeoff = ttk.Button(action_frame, text="起飞 (Takeoff)", command=lambda: self.send_command(self.tello.takeoff, blocking=True))
        btn_takeoff.pack(fill="x", padx=5, pady=2)
        self.action_buttons.append(btn_takeoff)

        btn_land = ttk.Button(action_frame, text="降落 (Land)", command=lambda: self.send_command(self.tello.land, blocking=True))
        btn_land.pack(fill="x", padx=5, pady=2)
        self.action_buttons.append(btn_land)

        btn_stop = tk.Button(action_frame, text="紧急停止 (EMERGENCY)", bg="red", fg="white", command=self.on_emergency)
        btn_stop.pack(fill="x", padx=5, pady=5)
        # Stop is NOT added to action_buttons list because it should always be enabled

        # Direction Control
        rc_frame = ttk.LabelFrame(control_panel, text="飞行控制")
        rc_frame.pack(fill="x", pady=5)

        # Grid for directional buttons
        btn_w = 6

        # Helper to create RC button
        def create_rc_btn(txt, r, c, lr, fb, ud, y):
            btn = ttk.Button(rc_frame, text=txt, width=btn_w, command=lambda: self.send_rc(lr, fb, ud, y))
            btn.grid(row=r, column=c, pady=2)
            self.action_buttons.append(btn)

        # Position / Movement (WASD equivalent)
        create_rc_btn("前", 0, 1, 0, 30, 0, 0)
        create_rc_btn("左", 1, 0, -30, 0, 0, 0)
        create_rc_btn("右", 1, 2, 30, 0, 0, 0)
        create_rc_btn("后", 2, 1, 0, -30, 0, 0)

        # Separator or Space
        ttk.Label(rc_frame, text="   ").grid(row=0, column=3)

        # Altitude / Rotation
        create_rc_btn("上升", 0, 4, 0, 0, 30, 0)
        create_rc_btn("左旋", 1, 3, 0, 0, 0, -30)
        create_rc_btn("右旋", 1, 5, 0, 0, 0, 30)
        create_rc_btn("下降", 2, 4, 0, 0, -30, 0)

        # Stop RC
        btn_hover = ttk.Button(rc_frame, text="悬停 (Stop)", command=lambda: self.send_rc(0, 0, 0, 0))
        btn_hover.grid(row=3, column=0, columnspan=6, sticky="ew", pady=5)
        self.action_buttons.append(btn_hover)

        # Instructions
        ttk.Label(control_panel, text="提示: 请先连接无人机。\n默认端口8889。", font=("Arial", 9), wraplength=200).pack(pady=10)

    def on_connect(self):
        ip = self.ip_var.get()
        if self.use_mock_var.get():
            print("Using Mock Tello")
            self.tello = MockTello(host=ip)
        else:
            print(f"Connecting to Real Tello at {ip}")
            self.tello = Tello(host=ip)
            try:
                port = int(self.port_var.get())
                if port != 8889:
                     print(f"Warning: Custom port {port} requested. Standard Tello port is 8889.")
                     self.tello.tello_addr = (ip, port)
            except ValueError:
                print("Invalid port, using default 8889")

        self.btn_connect.config(state="disabled")
        self.status_var.set("状态: 连接中...")

        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        try:
            self.tello.connect()
            self.tello.streamon()
            self.is_connected = True

            self.video_thread_running = True
            threading.Thread(target=self._video_loop, daemon=True).start()

            self.status_thread_running = True
            threading.Thread(target=self._status_loop, daemon=True).start()

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
                    img = cv2.resize(frame, (640, 480))
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(img)
                    self.root.after(0, self._update_video_label, img_pil)
                time.sleep(0.03)
            except Exception as e:
                print(f"Video loop error: {e}")
                time.sleep(1)

    def _update_video_label(self, img_pil):
        img_tk = ImageTk.PhotoImage(image=img_pil)
        self.video_label.configure(image=img_tk)
        self.video_label.image = img_tk

    def _status_loop(self):
        while self.status_thread_running:
            if self.tello:
                try:
                    bat = self.tello.get_battery()
                    self.root.after(0, lambda b=bat: self.battery_var.set(f"电量: {b}%"))
                except:
                    pass
            time.sleep(5)

    # --- Command Queue Logic ---

    def _command_worker(self):
        """Worker thread to process commands sequentially."""
        while self.queue_thread_running:
            try:
                # Get command from queue
                cmd_item = self.command_queue.get(timeout=1)
                func, args, is_blocking = cmd_item

                if is_blocking:
                    # Signal UI to lock
                    self.root.after(0, lambda: self._set_ui_busy(True))

                try:
                    func(*args)
                except Exception as e:
                    print(f"Command execution error: {e}")

                if is_blocking:
                    # Signal UI to unlock
                    self.root.after(0, lambda: self._set_ui_busy(False))

                self.command_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")

    def _set_ui_busy(self, busy):
        """Enable or disable action buttons."""
        self.is_executing_blocking_cmd = busy
        state = "disabled" if busy else "normal"

        status_text = "状态: 执行指令中..." if busy else "状态: 已连接"
        self.status_var.set(status_text)

        for btn in self.action_buttons:
            try:
                btn.config(state=state)
            except:
                pass # Button might be destroyed if closing

    def send_command(self, func, *args, blocking=False):
        """Queue a command."""
        if not self.is_connected:
            messagebox.showwarning("警告", "请先连接无人机")
            return

        if self.is_executing_blocking_cmd:
            # If busy, we reject new input as per user requirement "limit input"
            # Alternatively, we could queue it, but user asked to "wait until finish before inputting next".
            print("Command rejected: System is busy.")
            return

        self.command_queue.put((func, args, blocking))

    def send_rc(self, lr, fb, ud, y):
        # RC commands are generally non-blocking for the drone (updates velocity),
        # but we treat them as fast commands in the queue to avoid socket overlap.
        # They are NOT 'blocking' in the sense of locking the UI.
        # However, if a Blocking Command (Takeoff) is running, send_command check will reject this.
        self.send_command(self.tello.send_rc_control, lr, fb, ud, y, blocking=False)

    def on_emergency(self):
        """Emergency stop - bypass queue and clear it."""
        if self.tello:
            # Clear queue
            with self.command_queue.mutex:
                self.command_queue.queue.clear()

            # Send emergency immediately in a separate thread to bypass worker if it's stuck
            threading.Thread(target=self.tello.emergency, daemon=True).start()

            # Reset UI state immediately
            self.root.after(0, lambda: self._set_ui_busy(False))

if __name__ == "__main__":
    root = tk.Tk()
    app = TelloGUI(root)
    root.mainloop()
