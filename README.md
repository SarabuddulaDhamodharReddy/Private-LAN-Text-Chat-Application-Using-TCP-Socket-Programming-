# Private LAN Text Chat Application Using TCP Socket Programming

A Python-based **Private LAN Text Chat Application** that allows multiple computers connected to the same Local Area Network (LAN) to communicate through private, one-to-one text messages.

The application follows a **Client-Server Architecture**, where a central server manages client connections and forwards messages to their intended recipients.

The graphical user interface is developed using Python Tkinter, while TCP sockets handle reliable communication between computers.

## Features

- **Client-Server Communication:** Connect multiple client computers to a central server.
- **Private Messaging:** Send messages directly to a selected online user.
- **Online Users List:** View the users currently connected to the server.
- **Graphical User Interface:** Simple and interactive interface using Tkinter.
- **Multithreading:** Handle multiple client connections simultaneously.
- **TCP Communication:** Reliable data transmission using TCP sockets.
- **JSON-Based Protocol:** Exchange structured messages between clients and the server.
- **LAN Support:** Communicate between computers connected to the same local network.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Socket Programming | Network communication |
| TCP | Reliable data transmission |
| Tkinter | Graphical user interface |
| JSON | Message serialization |
| Threading | Concurrent client handling |

## Project Structure

```text
Private-LAN-Chat/
│
├── server.py          # Central server
├── client_gui.py      # Client graphical interface
└── README.md          # Project documentation
```

## Prerequisites

Before running the application, ensure that you have:

1. Python 3 installed on your computer.
2. Two or more computers connected to the same LAN.
3. Permission to configure Windows Firewall on the server computer.
4. A terminal or command prompt to execute Python files.

Check whether Python is installed:

```bash
python --version
```

If Python is installed, the version number will be displayed.

For Windows, download Python from:

https://www.python.org/downloads/

During installation, enable **Add Python to PATH**.

Tkinter is generally included with the standard Windows Python installation. On some Linux distributions, it may need to be installed separately.

## Installation and Setup

### Step 1: Clone the Repository

Open a terminal and execute:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
```

Navigate to the downloaded project directory:

```bash
cd Private-LAN-Chat
```

Alternatively, download the repository as a ZIP file and extract it.

### Step 2: Identify the Server Computer's IP Address

Choose one computer to act as the server.

On the server computer, open Command Prompt and execute:

```bash
ipconfig
```

Find the IPv4 Address under the network adapter currently connected to your LAN.

This address will be used by all client computers to connect to the server.

**Important:** The server computer and all client computers must be connected to a network that allows communication between them. A guest Wi-Fi network or network isolation setting may prevent direct connections.

### Step 3: Configure the Server

Open `server.py` and verify the server configuration.

The server should listen on all available network interfaces:

```python
HOST = "0.0.0.0"
PORT = 5000
```

`0.0.0.0` allows the server to accept connections through its available network interfaces.

Port `5000` is the default port used by this project. If you change it, update the client configuration accordingly.

### Step 4: Configure the Windows Firewall

The server computer must allow incoming TCP connections on the port used by the application.

Open **PowerShell as Administrator** on the server computer and execute:

```powershell
New-NetFirewallRule `
  -DisplayName "LAN Chat Application" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 5000 `
  -RemoteAddress LocalSubnet `
  -Action Allow
```

This creates an inbound firewall rule allowing TCP traffic on port `5000` from the local subnet.

To verify the firewall rule:

```powershell
Get-NetFirewallRule -DisplayName "LAN Chat Application"
```

**Note:** The firewall rule should only be created on the server computer. Follow your organization's network security policies when configuring firewall access.

### Step 5: Start the Server

On the server computer, open a terminal inside the project directory.

Execute:

```bash
python server.py
```

The server starts listening for incoming client connections.

**Expected output:**

```text
[SERVER STARTED] Listening on 0.0.0.0:5000
```

The exact output depends on the diagnostic messages implemented in `server.py`.

Keep this terminal running while using the application.

### Step 6: Configure the Client

On every client computer, open `client_gui.py`.

Locate the server configuration:

```python
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
```

Replace `127.0.0.1` with the actual IPv4 address of the computer running `server.py`.

For example:

```python
SERVER_HOST = "<SERVER_IP_ADDRESS>"
SERVER_PORT = 5000
```

Replace the placeholder with the server computer's current IPv4 address.

**Important:** Do not use `127.0.0.1` when connecting from another computer. It refers to that computer itself, not the remote server.

Save the file after updating the configuration.

### Step 7: Verify Network Connectivity

Before launching the client application, verify that the server is reachable.

On each client computer, open PowerShell and execute:

```powershell
Test-NetConnection <SERVER_IP_ADDRESS> -Port 5000
```

Replace `<SERVER_IP_ADDRESS>` with the actual server address.

A successful connection should display:

```text
TcpTestSucceeded : True
```

If the result is `False`, check the server status, server address, firewall settings, and network connectivity.

### Step 8: Launch the Client Application

On each client computer, navigate to the project directory and execute:

```bash
python client_gui.py
```

The graphical interface will open.

1. Enter a username.
2. Click **Connect**.
3. Wait for the connection to be established.
4. The online users list will display the connected users.
5. Select a user from the list.
6. Type a message and click **Send**.

Repeat these steps on other client computers to connect additional users.

## How the Application Works

The application follows a centralized client-server communication model.

1. The server starts and listens for incoming TCP connections.
2. Clients establish connections with the server.
3. Each client sends a login request containing its username.
4. The server registers the connected user and updates the online users list.
5. When a user selects another online user and sends a message, the client sends the message to the server.
6. The server identifies the intended recipient and forwards the message.
7. The recipient receives and displays the private message.

The application uses JSON messages separated by newline characters to exchange structured data over TCP connections.

## Troubleshooting

| Problem | Possible Solution |
|---|---|
| Server does not start | Check whether the configured port is already in use. |
| Client cannot connect | Verify the server IP address and port. |
| `TcpTestSucceeded : False` | Check firewall rules and LAN connectivity. |
| Client shows Disconnected | Ensure the server is running and the client configuration is correct. |
| Users are not visible | Verify that clients have successfully connected and logged in. |
| Messages are not delivered | Check the recipient's connection and server-side message handling. |
| Tkinter module not found | Install the Tkinter package for your Python distribution. |

## Important Notes

- The server must remain running while clients are connected.
- All computers must be able to communicate over the same LAN.
- The server's IP address may change when the network uses DHCP. Update `SERVER_HOST` in the client configuration whenever necessary.
- The configured port must be the same in both the server and client applications.
- This project is intended for local network communication and does not currently provide internet-based communication.
- Usernames are used to identify participants; they should not be treated as secure authentication credentials.
- Messages are not end-to-end encrypted. Avoid sending sensitive information through this application.

## Future Enhancements

- User authentication and password protection.
- End-to-end message encryption.
- Persistent chat history.
- File sharing between users.
- Message delivery and read receipts.
- Improved connection recovery and error handling.

## Learning Outcomes

This project demonstrates practical implementation of:

- TCP socket programming.
- Client-server architecture.
- Multithreaded network applications.
- GUI development using Tkinter.
- JSON-based communication protocols.
- LAN configuration and firewall management.

## Author

Developed as an academic course-based project to understand computer networking concepts and Python socket programming.

## License

This project is available for educational and learning purposes. Add a suitable open-source license to the repository if you want others to reuse, modify, and distribute the code under clearly defined terms."# Private-LAN-Text-Chat-Application-Using-TCP-Socket-Programming-" 
