# peer.py
import socket
import threading
import datetime
import time
import subprocess
import hashlib

# ---------------------------------------------------------------------------
# Message class to represent a gossip message.
# It stores the message text, its SHA-256 hash, a list of sender info,
# and a list of connections to which the message has been forwarded.
# ---------------------------------------------------------------------------
class Message:
    def __init__(self, message):
        self.message = message
        # Compute hash for the message to avoid duplicate processing.
        self.hash = hashlib.sha256(message.encode()).hexdigest()
        self.received_from = []  # List of sender identifiers (e.g., (ip, port) tuples).
        self.sent_to = []        # List of destination identifiers (e.g., (ip, port) tuples).

# ---------------------------------------------------------------------------
# Peer class: Implements a peer node in the P2P gossip network.
# Handles connecting to seed nodes and other peers, receiving and forwarding
# messages, and monitoring peer liveness via a heartbeat mechanism.
# ---------------------------------------------------------------------------
class Peer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        # Create a socket for listening for incoming peer connections.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow the socket to reuse the address (helps during restarts).
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.seed = []       # List of connections to seed nodes.
        # List of connected peers: each element is [peer_ip, peer_port, connection].
        self.connected = []
        self.logfile = f"logfile_peer_{self.port}.txt"  # Log file name based on peer port.
        # Set of peer info tuples received from seed nodes.
        self.peers = set()
        # Message List (ML): stores Message objects to avoid duplicate processing.
        self.messages = []
        # Mapping from connection object to the designated (listening) peer port.
        self.conn_designated = {}

    # -----------------------------------------------------------------------
    # Logging function: Prints messages to the console and appends them to a log file.
    # -----------------------------------------------------------------------
    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(self.logfile, "a") as f:
            f.write(log_message + "\n")

    # -----------------------------------------------------------------------
    # Helper function to obtain connection information.
    # Returns a string showing both the ephemeral (OS-assigned) port and
    # the designated port (if known) for clarity.
    # -----------------------------------------------------------------------
    def get_conn_info(self, connection):
        try:
            # Get the remote address and ephemeral port.
            ephemeral = connection.getpeername()  # Format: (ip, ephemeral_port)
        except Exception:
            ephemeral = ("unknown", "unknown")
        designated = self.conn_designated.get(connection, None)
        if designated:
            return f"{ephemeral} [Designated: {designated[1]}]"
        else:
            return str(ephemeral)

    # -----------------------------------------------------------------------
    # Connect to another peer using its IP and designated listening port.
    # Registers with the peer, starts a thread for handling incoming messages,
    # and also starts a heartbeat thread to monitor the connection.
    # -----------------------------------------------------------------------
    def connect_to_peer(self, peer_ip, peer_port):
        try:
            # Create a connection to the remote peer.
            connection = socket.create_connection((peer_ip, peer_port))
            self.connected.append([peer_ip, peer_port, connection])
            # Map the connection to its designated peer info.
            self.conn_designated[connection] = (peer_ip, peer_port)
            self.log(f"Connected to peer {peer_ip}:{peer_port} (Ephemeral: {connection.getsockname()[1]})")
            # Send a registration message to the connected peer.
            store_msg = f"STORE-{self.host}:{self.port}"
            connection.sendall(store_msg.encode())
            # Start a thread to handle incoming messages from this peer.
            threading.Thread(target=self.handle_peer_connection, args=(connection,), daemon=True).start()
            # Start a heartbeat thread to check liveness of the connection.
            threading.Thread(target=self.heartbeat, args=(connection, peer_ip, peer_port), daemon=True).start()
        except Exception as e:
            self.log(f"Failed to connect to peer {peer_ip}:{peer_port}. Error: {e}")

    # -----------------------------------------------------------------------
    # Connect to a seed node using its IP and port.
    # Registers with the seed and starts a thread to handle incoming seed messages.
    # -----------------------------------------------------------------------
    def connect_to_seed(self, seed_ip, seed_port):
        try:
            connection = socket.create_connection((seed_ip, seed_port))
            self.seed.append(connection)
            self.log(f"Connected to seed {seed_ip}:{seed_port} (Ephemeral: {connection.getsockname()[1]})")
            # Send a registration message to the seed.
            store_msg = f"STORE-{self.host}:{self.port}"
            connection.sendall(store_msg.encode())
            # Start a thread to handle incoming messages from the seed.
            threading.Thread(target=self.handle_seed_connection, args=(connection,), daemon=True).start()
        except Exception as e:
            self.log(f"Failed to connect to seed {seed_ip}:{seed_port}. Error: {e}")

    # -----------------------------------------------------------------------
    # Handle messages coming from a seed node.
    # Processes peer list updates and dead node notifications.
    # -----------------------------------------------------------------------
    def handle_seed_connection(self, connection):
        while True:
            try:
                data = connection.recv(1024)
                if not data:
                    break
                data = data.decode().strip()
                self.log(f"Received from seed {self.get_conn_info(connection)}: {data}")
                if data.startswith("PEERS:"):
                    # Expected format: PEERS:<ip>:<port>;<ip>:<port>;...
                    peers_str = data.split("PEERS:")[1]
                    if peers_str:
                        entries = peers_str.split(";")
                        for entry in entries:
                            if entry:
                                ip, port = entry.split(":")
                                self.peers.add((ip, int(port)))
                                self.log(f"Updated peer list with: {ip}:{port}")
                elif data.startswith("Dead Node:"):
                    self.log(f"Dead node reported: {data}")
            except Exception as e:
                self.log(f"Error in seed connection: {e}")
                break
        connection.close()

    # -----------------------------------------------------------------------
    # Handle incoming messages from another peer.
    # Processes registration messages, dead node notifications, and gossip messages.
    # For new gossip messages, the message is forwarded to all connected peers (except sender).
    # -----------------------------------------------------------------------
    def handle_peer_connection(self, connection):
        while True:
            try:
                data = connection.recv(1024)
                if not data:
                    break
                data = data.decode().strip()
                sender_info = self.get_conn_info(connection)
                self.log(f"Received from peer {sender_info}: {data}")
                if data.startswith("STORE-"):
                    # Process registration message from peer.
                    try:
                        host_port_str = data.split("STORE-")[1]
                        ip, port = host_port_str.split(":")
                        port = int(port)
                        # Update the mapping for the designated port.
                        self.conn_designated[connection] = (ip, port)
                        # Add the peer to the connected list if not already present.
                        if (ip, port) not in [(p[0], p[1]) for p in self.connected]:
                            self.connected.append([ip, port, connection])
                    except Exception as e:
                        self.log(f"Error parsing STORE message: {e}")
                elif data.startswith("Dead Node:"):
                    self.log(f"Received dead node message: {data}")
                elif ":" in data:
                    # Assume the data is a gossip message in the expected format.
                    msg_hash = hashlib.sha256(data.encode()).hexdigest()
                    # Only process if the message has not been seen before.
                    if not any(m.hash == msg_hash for m in self.messages):
                        new_msg = Message(data)
                        new_msg.received_from.append(self.get_conn_info(connection))
                        self.messages.append(new_msg)
                        self.log(f"New gossip message received: {data}")
                        # Forward the gossip message to all peers except the sender.
                        self.forward_message(data, exclude=connection)
            except Exception as e:
                self.log(f"Error handling peer connection: {e}")
                break
        connection.close()

    # -----------------------------------------------------------------------
    # Forward a message to all connected peers except the one specified in 'exclude'.
    # Logs the forwarding event along with connection details.
    # -----------------------------------------------------------------------
    def forward_message(self, message, exclude=None):
        for peer in self.connected:
            peer_ip, peer_port, conn = peer
            try:
                # Skip forwarding to the excluded connection.
                if exclude and conn.getpeername() == exclude.getpeername():
                    continue
            except Exception:
                pass
            try:
                conn.sendall(message.encode())
                self.log(f"Forwarded message to {peer_ip}:{peer_port} (Ephemeral: {conn.getsockname()[1]}) : {message}")
            except Exception as e:
                self.log(f"Failed to forward message to {peer_ip}:{peer_port} (Ephemeral: {conn.getsockname()[1]}): {e}")

    # -----------------------------------------------------------------------
    # Ping a given IP address using the system 'ping' command.
    # Returns True if the ping succeeds, False otherwise.
    # -----------------------------------------------------------------------
    def ping_peer(self, ip):
        try:
            # For Unix/Linux: using "-c 1" sends one ping request.
            # On Windows, replace "-c" with "-n" if needed.
            subprocess.check_output(["ping", "-c", "1", ip], stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            return False

    # -----------------------------------------------------------------------
    # Heartbeat mechanism: periodically pings a peer.
    # If 3 consecutive pings fail, the peer is marked as dead, removed, and
    # a dead node message is sent to all seed nodes.
    # -----------------------------------------------------------------------
    def heartbeat(self, connection, peer_ip, peer_port):
        failures = 0
        while failures < 3:
            time.sleep(13)
            if self.ping_peer(peer_ip):
                failures = 0
            else:
                failures += 1
                self.log(f"Ping failure {failures} for peer {peer_ip}:{peer_port} (Ephemeral: {connection.getsockname()[1]})")
        self.log(f"3 consecutive ping failures. Peer {peer_ip}:{peer_port} (Ephemeral: {connection.getsockname()[1]}) is dead.")
        # Remove the dead peer from the connected list.
        self.connected = [p for p in self.connected if not (p[0]==peer_ip and p[1]==peer_port)]
        # Report the dead node to all connected seed nodes.
        self.send_dead_node_to_seeds(peer_ip, peer_port)
        try:
            connection.close()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Send a dead node notification to all connected seed nodes.
    # The message format is: "Dead Node:<dead_ip>:<dead_port>:<timestamp>:<reporter_IP>"
    # -----------------------------------------------------------------------
    def send_dead_node_to_seeds(self, dead_ip, dead_port):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = f"Dead Node:{dead_ip}:{dead_port}:{timestamp}:{self.host}"
        for seed_conn in self.seed:
            try:
                seed_conn.sendall(data.encode())
                self.log(f"Sent dead node message to seed {seed_conn.getpeername()}: {data}")
            except Exception as e:
                self.log(f"Failed to send dead node message to seed: {e}")

    # -----------------------------------------------------------------------
    # Gossip function: Generates and broadcasts exactly 10 gossip messages,
    # one every 5 seconds. The message index is displayed starting at 1 for clarity.
    # -----------------------------------------------------------------------
    def gossip(self):
        for i in range(10):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Message format: "<timestamp>:<host>:Msg#<i+1> - Gossip broadcast from <host>:<port>"
            message_text = f"{timestamp}:{self.host}:Msg#{i+1} - Gossip broadcast from {self.host}:{self.port}"
            new_msg = Message(message_text)
            # Log that this message originates from this peer.
            new_msg.received_from.append(f"Designated: {self.host}:{self.port}")
            self.messages.append(new_msg)
            self.log(f"Broadcasting gossip message ({i+1}/10): {message_text}")
            # Forward the gossip message to all connected peers.
            self.forward_message(message_text)
            time.sleep(5)

    # -----------------------------------------------------------------------
    # Listen for incoming peer connections.
    # Binds the peer's listening socket to its host and port.
    # For each accepted connection, starts threads for handling messages and heartbeat.
    # -----------------------------------------------------------------------
    def listen(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        self.log(f"Listening for peer connections on {self.host}:{self.port}")
        while True:
            try:
                conn, addr = self.socket.accept()
                self.log(f"Accepted connection from peer {addr} (Ephemeral: {conn.getsockname()[1]})")
                threading.Thread(target=self.handle_peer_connection, args=(conn,), daemon=True).start()
                # Start heartbeat for the incoming connection using the address info.
                threading.Thread(target=self.heartbeat, args=(conn, addr[0], addr[1]), daemon=True).start()
            except Exception as e:
                self.log(f"Error accepting peer connection: {e}")
                break

    # -----------------------------------------------------------------------
    # Start the peer node: begins listening for incoming connections and starts the gossip thread.
    # -----------------------------------------------------------------------
    def start(self):
        threading.Thread(target=self.listen, daemon=True).start()
        # Wait a short period to allow initial connections to be established.
        time.sleep(3)
        threading.Thread(target=self.gossip, daemon=True).start()

    # -----------------------------------------------------------------------
    # Close all connections and shut down the peer's listening socket.
    # Logs the closure events.
    # -----------------------------------------------------------------------
    def close_socket(self):
        self.log("Closing all connections.")
        try:
            for peer in self.connected:
                try:
                    peer[2].close()
                except:
                    pass
            for seed_conn in self.seed:
                try:
                    seed_conn.close()
                except:
                    pass
            self.socket.close()
            self.log("Peer closed successfully.")
        except Exception as e:
            self.log(f"Error closing the peer: {e}")
