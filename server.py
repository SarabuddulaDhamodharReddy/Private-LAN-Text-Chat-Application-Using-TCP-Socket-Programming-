import json
import socket
import threading
from datetime import datetime

# ============================================================
# PRIVATE LAN CHAT SERVER
# Run this server on the computer designated as the server.
# ============================================================

HOST = "0.0.0.0"
PORT = 5000
MAX_MESSAGE_LENGTH = 2000
MAX_PACKET_LENGTH = 12000

# username -> ChatClient
clients = {}
clients_lock = threading.Lock()


def log(message):
    """Print a timestamped server log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


class ChatClient:
    def __init__(self, sock, address):
        self.sock = sock
        self.address = address
        self.username = None
        self.send_lock = threading.Lock()

    def send(self, packet):
        """Send one JSON packet, safely serialized as a line."""
        data = (
            json.dumps(packet, ensure_ascii=False) + "\n"
        ).encode("utf-8")

        with self.send_lock:
            self.sock.sendall(data)


def send_users():
    """Notify connected clients whenever the online list changes."""
    with clients_lock:
        recipients = list(clients.values())
        usernames = sorted(clients.keys(), key=str.casefold)

    packet = {
        "type": "users",
        "users": usernames
    }

    log(f"[USERS] Online users: {usernames}")

    for recipient in recipients:
        try:
            recipient.send(packet)
        except (OSError, ConnectionError) as error:
            log(
                f"[WARN] Could not update user list for "
                f"{recipient.username}: {error}"
            )


def handle_client(sock, address):
    client = ChatClient(sock, address)
    reader = None
    logged_in = False

    log(f"[DEBUG] Handler started for {address}")

    try:
        reader = sock.makefile(
            "r",
            encoding="utf-8",
            newline="\n"
        )

        # 1. Wait for the initial login packet.
        log(f"[DEBUG] Waiting for login packet from {address}")

        line = reader.readline(MAX_PACKET_LENGTH + 1)

        log(f"[DEBUG] Login data received from {address}: {line[:300]!r}")

        if not line:
            log(f"[WARN] Client {address} closed before login.")
            return

        if len(line) > MAX_PACKET_LENGTH:
            client.send({
                "type": "error",
                "text": "Login packet is too large."
            })
            return

        try:
            request = json.loads(line)
        except json.JSONDecodeError as error:
            log(f"[ERROR] Invalid login JSON from {address}: {error}")
            client.send({
                "type": "error",
                "text": "Invalid login packet."
            })
            return

        if not isinstance(request, dict):
            client.send({
                "type": "error",
                "text": "Invalid login request."
            })
            return

        if request.get("type") != "login":
            log(f"[WARN] Expected login packet from {address}")
            client.send({
                "type": "error",
                "text": "Login required."
            })
            return

        username = request.get("username", "")

        if not isinstance(username, str):
            username = ""

        username = username.strip()

        if (
            not username
            or len(username) > 20
            or any(ord(ch) < 32 for ch in username)
        ):
            log(f"[WARN] Invalid username from {address}")
            client.send({
                "type": "error",
                "text": "Username must contain 1–20 valid characters."
            })
            return

        # 2. Register a unique online username.
        with clients_lock:
            duplicate = any(
                existing.casefold() == username.casefold()
                for existing in clients
            )

            if not duplicate:
                client.username = username
                clients[username] = client

        if duplicate:
            log(f"[LOGIN REJECTED] Duplicate username: {username}")
            client.send({
                "type": "error",
                "text": "That username is already online."
            })
            return

        try:
            client.send({
                "type": "login_ok",
                "username": username
            })
        except (OSError, ConnectionError):
            log(f"[ERROR] Could not confirm login for {username}")
            return

        logged_in = True
        log(f"[LOGIN SUCCESS] {username} connected from {address}")

        send_users()

        # 3. Receive private messages from this client.
        while True:
            line = reader.readline(MAX_PACKET_LENGTH + 1)

            if not line:
                log(f"[DEBUG] Connection closed by {username}")
                break

            if len(line) > MAX_PACKET_LENGTH:
                log(f"[WARN] Oversized packet from {username}")
                try:
                    client.send({
                        "type": "error",
                        "text": "Packet too large."
                    })
                except OSError:
                    break
                continue

            try:
                packet = json.loads(line)
            except json.JSONDecodeError as error:
                log(f"[WARN] Invalid JSON from {username}: {error}")
                client.send({
                    "type": "error",
                    "text": "Invalid message format."
                })
                continue

            if not isinstance(packet, dict):
                continue

            packet_type = packet.get("type")

            if packet_type == "ping":
                client.send({"type": "pong"})
                continue

            if packet_type != "private":
                log(
                    f"[WARN] Unexpected packet type "
                    f"from {username}: {packet_type!r}"
                )
                continue

            recipient_name = packet.get("to")
            message = packet.get("text")

            if (
                not isinstance(recipient_name, str)
                or not isinstance(message, str)
            ):
                client.send({
                    "type": "error",
                    "text": "Invalid recipient or message."
                })
                continue

            message = message.strip()

            if not message:
                continue

            if len(message) > MAX_MESSAGE_LENGTH:
                client.send({
                    "type": "error",
                    "text": "Message exceeds 2000 characters."
                })
                continue

            if any(
                ord(ch) < 32 and ch not in "\t"
                for ch in message
            ):
                client.send({
                    "type": "error",
                    "text": "Message contains unsupported control characters."
                })
                continue

            if recipient_name.casefold() == username.casefold():
                client.send({
                    "type": "error",
                    "text": "You cannot message yourself."
                })
                continue

            # Resolve the recipient using the registered username.
            with clients_lock:
                actual_name = next(
                    (
                        name for name in clients
                        if name.casefold() == recipient_name.casefold()
                    ),
                    None
                )
                recipient = clients.get(actual_name) if actual_name else None

            if recipient is None:
                log(
                    f"[DELIVERY FAILED] {username} -> "
                    f"{recipient_name}: recipient offline"
                )
                client.send({
                    "type": "error",
                    "text": f"{recipient_name} is no longer online."
                })
                continue

            timestamp = datetime.now().strftime("%H:%M")

            message_packet = {
                "type": "private_message",
                "from": username,
                "to": actual_name,
                "text": message,
                "time": timestamp
            }

            # Deliver to the sender and intended recipient only.
            try:
                client.send(message_packet)
                recipient.send(message_packet)

                log(
                    f"[PRIVATE MESSAGE] {username} -> "
                    f"{actual_name}: {message}"
                )

            except (OSError, ConnectionError) as error:
                log(f"[DELIVERY ERROR] {error}")

                try:
                    client.send({
                        "type": "error",
                        "text": "Delivery failed. Please reconnect if needed."
                    })
                except OSError:
                    pass

    except (OSError, ConnectionError, UnicodeError) as error:
        log(f"[CONNECTION ERROR] {address}: {error}")

    except Exception as error:
        # Keep unexpected bugs visible during development.
        log(f"[UNEXPECTED ERROR] {address}: {error}")
        import traceback
        traceback.print_exc()

    finally:
        if reader is not None:
            try:
                reader.close()
            except (OSError, ValueError):
                pass

        removed = False

        with clients_lock:
            # Avoid deleting a newer connection with the same username.
            if (
                client.username
                and clients.get(client.username) is client
            ):
                del clients[client.username]
                removed = True

        try:
            sock.close()
        except OSError:
            pass

        if removed:
            log(f"[DISCONNECTED] {client.username} ({address})")

        if removed and logged_in:
            send_users()

        log(f"[DEBUG] Handler finished for {address}")


def main():
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )
    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    try:
        server.bind((HOST, PORT))
        server.listen(20)

        print("=" * 55, flush=True)
        print("           PRIVATE LAN CHAT SERVER", flush=True)
        print("=" * 55, flush=True)
        log(f"[STARTED] Listening on {HOST}:{PORT}")
        log("[INFO] Waiting for users...")
        log("[INFO] Press Ctrl+C to stop the server.")

        while True:
            sock, address = server.accept()

            log(f"[TCP ACCEPTED] Connection from {address}")

            thread = threading.Thread(
                target=handle_client,
                args=(sock, address),
                daemon=True
            )
            thread.start()

    except KeyboardInterrupt:
        log("[SHUTDOWN] Server shutdown requested.")

    except OSError as error:
        log(f"[SERVER ERROR] {error}")

    finally:
        with clients_lock:
            active_clients = list(clients.values())
            clients.clear()

        for client in active_clients:
            try:
                client.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                client.sock.close()
            except OSError:
                pass

        server.close()
        log("[STOPPED] Server has stopped.")


if __name__ == "__main__":
    main()
