
import json
import queue
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ==========================================================
# PRIVATE LAN CHAT - CLIENT GUI
# Update SERVER_HOST if your server's IP address changes.
# ==========================================================

SERVER_HOST = "YOUR_SERVER_IP_ADDRESS"  # Replace with the server computer's IPv4 address
SERVER_PORT = 5000
MAX_MESSAGE_LENGTH = 2000


class PrivateLANChat:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Chat | Private Messenger")
        self.root.geometry("1000x650")
        self.root.minsize(760, 480)
        self.root.configure(bg="#F3F5F9")

        self.sock = None
        self.send_lock = threading.Lock()
        self.events = queue.Queue()

        self.connected = False
        self.closing = False
        self.username = ""
        self.active_user = None

        self.users = []
        self.histories = {}
        self.unread = {}

        self.setup_styles()
        self.build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
        self.root.after(100, self.process_events)

    # ------------------------------------------------------
    # STYLES
    # ------------------------------------------------------

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "TButton",
            font=("Segoe UI", 10),
            padding=(10, 7)
        )

        style.configure(
            "TEntry",
            font=("Segoe UI", 11),
            padding=7
        )

    # ------------------------------------------------------
    # USER INTERFACE
    # ------------------------------------------------------

    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#FFFFFF", height=68)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="●",
            fg="#2563EB",
            bg="#FFFFFF",
            font=("Segoe UI", 22)
        ).pack(side="left", padx=(20, 8))

        tk.Label(
            header,
            text="LAN Chat",
            fg="#172033",
            bg="#FFFFFF",
            font=("Segoe UI", 19, "bold")
        ).pack(side="left")

        self.connection_label = tk.Label(
            header,
            text="● Disconnected",
            fg="#64748B",
            bg="#FFFFFF",
            font=("Segoe UI", 10)
        )
        self.connection_label.pack(side="right", padx=20)

        # Main body
        body = tk.Frame(self.root, bg="#F3F5F9")
        body.pack(
            side="top",
            fill="both",
            expand=True,
            padx=14,
            pady=14
        )

        # Sidebar
        sidebar = tk.Frame(
            body,
            bg="#FFFFFF",
            width=255
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="YOUR PROFILE",
            bg="#FFFFFF",
            fg="#8490A5",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=16, pady=(16, 7))

        self.username_entry = ttk.Entry(sidebar)
        self.username_entry.pack(fill="x", padx=14)
        # Enter a username when the application starts.

        self.connect_button = ttk.Button(
            sidebar,
            text="Connect to server",
            command=self.connect
        )
        self.connect_button.pack(
            fill="x", padx=14, pady=(8, 5)
        )

        self.disconnect_button = ttk.Button(
            sidebar,
            text="Disconnect",
            command=self.disconnect,
            state="disabled"
        )
        self.disconnect_button.pack(fill="x", padx=14)

        tk.Frame(
            sidebar,
            bg="#E8ECF3",
            height=1
        ).pack(fill="x", padx=14, pady=15)

        tk.Label(
            sidebar,
            text="PEOPLE",
            bg="#FFFFFF",
            fg="#8490A5",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.user_list = tk.Listbox(
            sidebar,
            font=("Segoe UI", 11),
            bg="#FFFFFF",
            fg="#253047",
            selectbackground="#E7EEFF",
            selectforeground="#1D4ED8",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            exportselection=False
        )
        self.user_list.pack(
            fill="both", expand=True, padx=8, pady=(0, 10)
        )
        self.user_list.bind(
            "<<ListboxSelect>>", self.select_user
        )

        tk.Label(
            sidebar,
            text="Select a person to chat privately.",
            bg="#FFFFFF",
            fg="#8490A5",
            font=("Segoe UI", 9),
            wraplength=215
        ).pack(anchor="w", padx=14, pady=(0, 14))

        # Conversation panel
        conversation = tk.Frame(body, bg="#FFFFFF")
        conversation.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(12, 0)
        )

        # Conversation title
        title_panel = tk.Frame(
            conversation,
            bg="#FFFFFF",
            padx=20,
            pady=14
        )
        title_panel.pack(side="top", fill="x")

        self.chat_title = tk.Label(
            title_panel,
            text="Welcome to LAN Chat",
            bg="#FFFFFF",
            fg="#172033",
            font=("Segoe UI", 15, "bold"),
            anchor="w"
        )
        self.chat_title.pack(fill="x")

        self.chat_subtitle = tk.Label(
            title_panel,
            text="Connect to see who's online.",
            bg="#FFFFFF",
            fg="#8490A5",
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.chat_subtitle.pack(fill="x", pady=(4, 0))

        tk.Frame(
            conversation,
            bg="#E8ECF3",
            height=1
        ).pack(side="top", fill="x")

        # IMPORTANT: Pack the composer FIRST at the bottom.
        # This reserves its space before the expandable chat area.
        composer = tk.Frame(
            conversation,
            bg="#F8FAFD",
            height=70,
            padx=14,
            pady=12
        )
        composer.pack(side="bottom", fill="x")
        composer.pack_propagate(False)

        self.message_entry = ttk.Entry(
            composer,
            font=("Segoe UI", 11)
        )
        self.message_entry.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )
        self.message_entry.bind(
            "<Return>", self.send_message
        )

        self.send_button = ttk.Button(
            composer,
            text="Send",
            command=self.send_message,
            state="disabled"
        )
        self.send_button.pack(side="right", fill="y")

        # Chat history takes the remaining space.
        chat_frame = tk.Frame(conversation, bg="#FFFFFF")
        chat_frame.pack(
            side="top",
            fill="both",
            expand=True
        )

        self.chat_area = tk.Text(
            chat_frame,
            wrap="word",
            state="disabled",
            bg="#FFFFFF",
            fg="#253047",
            font=("Segoe UI", 11),
            relief="flat",
            borderwidth=0,
            padx=20,
            pady=18,
            spacing1=3,
            spacing3=9
        )

        scrollbar = ttk.Scrollbar(
            chat_frame,
            orient="vertical",
            command=self.chat_area.yview
        )
        self.chat_area.configure(
            yscrollcommand=scrollbar.set
        )

        self.chat_area.pack(
            side="left", fill="both", expand=True
        )
        scrollbar.pack(side="right", fill="y")

        # Message formatting
        self.chat_area.tag_configure(
            "system",
            foreground="#8490A5",
            justify="center",
            font=("Segoe UI", 9)
        )

        self.chat_area.tag_configure(
            "own_name",
            foreground="#1D4ED8",
            font=("Segoe UI", 9, "bold")
        )

        self.chat_area.tag_configure(
            "other_name",
            foreground="#087F5B",
            font=("Segoe UI", 9, "bold")
        )

        self.chat_area.tag_configure(
            "bubble_own",
            background="#E7EEFF",
            foreground="#172033",
            lmargin1=16,
            lmargin2=16,
            rmargin=20,
            spacing1=7,
            spacing3=7
        )

        self.chat_area.tag_configure(
            "bubble_other",
            background="#F0F3F8",
            foreground="#172033",
            lmargin1=16,
            lmargin2=16,
            rmargin=20,
            spacing1=7,
            spacing3=7
        )

        self.chat_area.tag_configure(
            "time",
            foreground="#8490A5",
            font=("Segoe UI", 8)
        )

        self.show_placeholder()

    # ------------------------------------------------------
    # CHAT DISPLAY
    # ------------------------------------------------------

    def show_placeholder(self):
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")

        self.chat_area.insert(
            "end",
            "\n\nYour private conversations appear here.\n\n"
            "Connect and select someone from PEOPLE.",
            "system"
        )

        self.chat_area.configure(state="disabled")

    def add_system_message(self, text):
        if self.active_user:
            self.histories.setdefault(
                self.active_user, []
            ).append({
                "from": "System",
                "text": text,
                "time": datetime.now().strftime("%H:%M"),
                "mine": False,
                "system": True
            })

            self.render_history(self.active_user)
        else:
            self.chat_area.configure(state="normal")
            self.chat_area.insert(
                "end", f"\n{text}\n", "system"
            )
            self.chat_area.see("end")
            self.chat_area.configure(state="disabled")

    def render_history(self, peer):
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")

        history = self.histories.get(peer, [])

        if not history:
            self.chat_area.insert(
                "end",
                f"\n\nStart a private conversation with {peer}.",
                "system"
            )

        for item in history:
            if item.get("system"):
                self.chat_area.insert(
                    "end",
                    f'\n{item["text"]}\n',
                    "system"
                )
                continue

            name = "You" if item["mine"] else item["from"]
            name_tag = (
                "own_name" if item["mine"] else "other_name"
            )
            bubble_tag = (
                "bubble_own" if item["mine"]
                else "bubble_other"
            )

            self.chat_area.insert(
                "end", f"{name}  ", name_tag
            )
            self.chat_area.insert(
                "end", f'{item["time"]}\n', "time"
            )
            self.chat_area.insert(
                "end",
                f'  {item["text"]}  \n\n',
                bubble_tag
            )

        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    # ------------------------------------------------------
    # CONNECTION
    # ------------------------------------------------------

    def connect(self):
        username = self.username_entry.get().strip()

        if (
            not username
            or len(username) > 20
            or any(ord(ch) < 32 for ch in username)
        ):
            messagebox.showwarning(
                "Invalid username",
                "Enter a username of 1–20 characters."
            )
            return

        self.username = username
        self.connect_button.configure(state="disabled")
        self.username_entry.configure(state="disabled")
        self.connection_label.configure(
            text="● Connecting...",
            fg="#D97706"
        )

        threading.Thread(
            target=self.connection_worker,
            args=(username,),
            daemon=True
        ).start()

    def connection_worker(self, username):
        sock = None
        reader = None

        try:
            sock = socket.create_connection(
                (SERVER_HOST, SERVER_PORT),
                timeout=10
            )
            sock.settimeout(None)

            # Send login packet.
            payload = (
                json.dumps({
                    "type": "login",
                    "username": username
                }, ensure_ascii=False) + "\n"
            ).encode("utf-8")

            sock.sendall(payload)

            reader = sock.makefile(
                "r",
                encoding="utf-8",
                newline="\n"
            )

            # Wait for server's login response.
            line = reader.readline()

            if not line:
                raise ConnectionError(
                    "Server closed the connection during login."
                )

            response = json.loads(line)

            if response.get("type") != "login_ok":
                raise ConnectionError(
                    response.get("text", "Login rejected.")
                )

            # Publish the socket only after login succeeds.
            self.sock = sock
            self.events.put(("connected", None))

            for line in reader:
                if len(line) > 12000:
                    continue

                try:
                    packet = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if isinstance(packet, dict):
                    self.events.put(("packet", packet))

            self.events.put((
                "disconnected",
                "The server closed the connection."
            ))

        except (
            OSError,
            ConnectionError,
            UnicodeError,
            json.JSONDecodeError
        ) as error:
            self.events.put(("connection_error", str(error)))

        finally:
            if reader is not None:
                try:
                    reader.close()
                except (OSError, ValueError):
                    pass

            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

            if self.sock is sock:
                self.sock = None

    def process_events(self):
        try:
            while True:
                event, data = self.events.get_nowait()

                if event == "connected":
                    self.connected = True

                    self.connection_label.configure(
                        text=f"● Connected · {SERVER_HOST}",
                        fg="#15803D"
                    )

                    self.connect_button.configure(
                        state="disabled"
                    )
                    self.disconnect_button.configure(
                        state="normal"
                    )
                    self.send_button.configure(
                        state="normal"
                    )

                    self.add_system_message(
                        "Connected successfully."
                    )
                    self.message_entry.focus_set()

                elif event == "packet":
                    self.handle_packet(data)

                elif event == "connection_error":
                    self.reset_connection()
                    messagebox.showerror(
                        "Connection failed",
                        f"Could not connect or log in:\n\n{data}"
                    )

                elif event == "disconnected":
                    was_connected = self.connected
                    self.reset_connection()

                    if was_connected:
                        self.add_system_message(data)

        except queue.Empty:
            pass

        if not self.closing:
            self.root.after(100, self.process_events)

    # ------------------------------------------------------
    # USERS AND PRIVATE MESSAGES
    # ------------------------------------------------------

    def handle_packet(self, packet):
        kind = packet.get("type")

        if kind == "users":
            names = packet.get("users", [])

            if isinstance(names, list):
                self.users = [
                    name for name in names
                    if isinstance(name, str)
                    and name != self.username
                ]

                self.refresh_user_list()

                if (
                    self.active_user
                    and self.active_user not in self.users
                ):
                    self.chat_subtitle.configure(
                        text="Offline · Previous messages remain available"
                    )

        elif kind == "private_message":
            sender = packet.get("from")
            recipient = packet.get("to")
            text = packet.get("text", "")
            timestamp = packet.get("time", "")

            if sender == self.username:
                peer = recipient
                mine = True
            elif recipient == self.username:
                peer = sender
                mine = False
            else:
                return

            if not isinstance(peer, str):
                return

            self.histories.setdefault(peer, []).append({
                "from": sender,
                "text": text,
                "time": timestamp,
                "mine": mine
            })

            if self.active_user == peer:
                self.render_history(peer)
            elif not mine:
                self.unread[peer] = (
                    self.unread.get(peer, 0) + 1
                )

            self.refresh_user_list()

        elif kind == "error":
            self.add_system_message(
                "Server: " + packet.get("text", "Unknown error")
            )

    def refresh_user_list(self):
        selected_user = self.active_user

        self.user_list.delete(0, "end")

        for name in self.users:
            unread_count = self.unread.get(name, 0)

            label = f"●  {name}"
            if unread_count:
                label += f"   ({unread_count} new)"

            self.user_list.insert("end", label)

            index = self.user_list.size() - 1
            self.user_list.itemconfig(
                index,
                fg="#15803D"
            )

            if name == selected_user:
                self.user_list.selection_set(index)
                self.user_list.activate(index)

    def select_user(self, event=None):
        selection = self.user_list.curselection()

        if not selection:
            return

        index = selection[0]

        if index >= len(self.users):
            return

        self.active_user = self.users[index]
        self.unread[self.active_user] = 0

        self.chat_title.configure(
            text=self.active_user
        )
        self.chat_subtitle.configure(
            text="● Online · Private conversation",
            fg="#15803D"
        )

        self.refresh_user_list()
        self.render_history(self.active_user)
        self.message_entry.focus_set()

    # ------------------------------------------------------
    # SENDING MESSAGES
    # ------------------------------------------------------

    def send_packet(self, packet):
        payload = (
            json.dumps(packet, ensure_ascii=False) + "\n"
        ).encode("utf-8")

        # Prevent concurrent socket writes.
        with self.send_lock:
            if not self.connected or self.sock is None:
                raise ConnectionError(
                    "Not connected to the server."
                )

            self.sock.sendall(payload)

    def send_message(self, event=None):
        if not self.connected:
            return

        if not self.active_user:
            messagebox.showinfo(
                "Select a person",
                "Select a person from PEOPLE before sending a message."
            )
            return

        text = self.message_entry.get().strip()

        if not text:
            return

        if len(text) > MAX_MESSAGE_LENGTH:
            messagebox.showwarning(
                "Message too long",
                f"Messages must be at most {MAX_MESSAGE_LENGTH} characters."
            )
            return

        try:
            self.send_packet({
                "type": "private",
                "to": self.active_user,
                "text": text
            })

            self.message_entry.delete(0, "end")

        except (OSError, ConnectionError) as error:
            messagebox.showerror(
                "Send failed",
                str(error)
            )
            self.disconnect()

    # ------------------------------------------------------
    # DISCONNECT AND CLEANUP
    # ------------------------------------------------------

    def reset_connection(self):
        self.connected = False
        self.sock = None

        self.connection_label.configure(
            text="● Disconnected",
            fg="#64748B"
        )

        self.connect_button.configure(state="normal")
        self.username_entry.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.send_button.configure(state="disabled")

        self.users = []
        self.user_list.delete(0, "end")

    def disconnect(self):
        with self.send_lock:
            sock = self.sock
            self.sock = None
            self.connected = False

        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                sock.close()
            except OSError:
                pass

        self.reset_connection()

    def close_app(self):
        self.closing = True
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PrivateLANChat(root)
    root.mainloop()
