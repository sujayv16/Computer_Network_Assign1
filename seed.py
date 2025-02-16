# seed.py
import socket
import threading
import datetime

class Seed:
    def __init__(self, host, port):
        """
        Initialize the seed node with a given host and port.
        - Creates a TCP socket.
        - Sets socket option to reuse the address.
        - Initializes lists to track active connections and the peer list.
        """
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow the socket to reuse the address (helps during quick restarts)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.connections = []  # List of active socket connections from peers.
        self.logfile = f"logfile_seed_{self.port}.txt"  # Log file name based on port.
        self.peer_list = []    # List to store tuples (ip, port) of registered peers.

    def listen(self):
        """
        Bind the socket to the host and port, start listening for incoming connections.
        For each connection accepted, a new thread is spawned to handle the client.
        """
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        self.log(f"Listening for connections on {self.host}:{self.port}")

        while True:
            # Accept an incoming connection
            connection, address = self.socket.accept()
            self.connections.append(connection)
            self.log(f"Accepted connection from {address}")
            # Start a new thread to handle communication with the connected peer
            threading.Thread(target=self.handle_client, args=(connection, address), daemon=True).start()

    def send_data(self, connection, data):
        """
        Send a data string to a specified connection.
        Log the action and remove the connection if sending fails.
        """
        try:
            connection.sendall(data.encode())
            self.log(f"Sent data to {connection.getpeername()}: {data}")
        except socket.error as e:
            self.log(f"Failed to send data. Error: {e}")
            try:
                self.connections.remove(connection)
            except Exception:
                pass

    def send_peer_list(self, connection):
        """
        Format the current peer list into a string and send it to the given connection.
        Format: "PEERS:<ip>:<port>;<ip>:<port>;..."
        """
        data = "PEERS:" + ";".join(f"{ip}:{port}" for ip, port in self.peer_list)
        self.send_data(connection, data)

    def handle_client(self, connection, address):
        """
        Handle the communication with a connected peer.
        Immediately send the current peer list.
        Then, continuously listen for incoming data, parse it,
        and update the peer list or process dead node messages.
        """
        self.log(f"Connection from {address} opened.")
        # Send the current list of peers to the newly connected client
        self.send_peer_list(connection)
        while True:
            try:
                data = connection.recv(1024)
                if not data:
                    # If no data received, break the loop (connection closed)
                    break
                data = data.decode().strip()
                self.log(f"Received data from {address}: {data}")
                
                if data.startswith("STORE-"):
                    # Expected format: "STORE-<ip>:<port>"
                    try:
                        host_port_str = data.split("STORE-")[1]
                        host, port = host_port_str.split(":")
                        port = int(port)
                        # Add the peer to the peer_list if it's not already present
                        if (host, port) not in self.peer_list:
                            self.peer_list.append((host, port))
                            self.log(f"Added peer {host}:{port}. New peer list: {self.peer_list}")
                    except Exception as e:
                        self.log(f"Error parsing STORE message: {e}")
                        
                elif data.startswith("Dead Node:"):
                    # Expected format: "Dead Node:<DeadNode.IP>:<DeadNode.Port>:<timestamp>:<reporter.IP>"
                    try:
                        parts = data.split(":")
                        dead_ip = parts[1]
                        dead_port = int(parts[2])
                        # Remove the peer from the list if present
                        if (dead_ip, dead_port) in self.peer_list:
                            self.peer_list.remove((dead_ip, dead_port))
                            self.log(f"Removed dead peer {dead_ip}:{dead_port}. Updated peer list: {self.peer_list}")
                    except Exception as e:
                        self.log(f"Error parsing Dead Node message: {e}")
            except socket.error:
                # If a socket error occurs, exit the loop
                break

        self.log(f"Connection from {address} closed.")
        try:
            self.connections.remove(connection)
        except Exception:
            pass
        connection.close()

    def start(self):
        """
        Start the seed node's listening process on a new daemon thread.
        """
        threading.Thread(target=self.listen, daemon=True).start()

    def log(self, message):
        """
        Log a message with a timestamp.
        The message is printed to the console and also appended to the logfile.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(self.logfile, "a") as f:
            f.write(log_message + "\n")
