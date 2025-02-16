# Computer_Network_Assign1

This repository contains the implementation for Computer Networks Assignment 1: **Gossip Protocol over a Peer-to-Peer Network**.


## TEAM
- **Viswanadhapalli Sujay** (b22cs063)
- **Aiswarya** (b22cs28)

## Overview
This assignment implements a gossip protocol over a peer-to-peer network to:
- Broadcast messages reliably using a gossip protocol.
- Monitor the liveness of connected peers using system ping utilities.
- Ensure that each peer registers with a set of seed nodes, obtains a union of peer lists, and then establishes connections with selected peers.
- Simulate dead-node detection by intentionally closing one peer to test the functionality.

### Key Features
- **Peer Registration:**  
  Peers register with at least ⌊(n/2)⌋ + 1 seed nodes (where n is the total number of seed nodes) using a configuration file.
- **Peer Discovery:**  
  Peers retrieve peer lists from seeds and connect with a subset of peers (designed to mimic a power-law degree distribution, though in this version it's randomly selected).
- **Gossip Protocol:**  
  Each peer broadcasts exactly 10 gossip messages in the format:  
  `<timestamp>:<self.IP>:Msg#<i> - Gossip broadcast from <self.IP>:<self.port>`  
  (with the message index starting at 1 for clarity).
- **Message Forwarding:**  
  Peers forward each gossip message only once over each connection, avoiding loops.
- **Liveness Monitoring:**  
  Peers use a system ping command to monitor connected peers. If 3 consecutive ping attempts fail, the peer is marked as dead and a dead node message is sent to the seed nodes.
- **Logging:**  
  All nodes log actions to both the console and log files. Logs include both the ephemeral port (OS-assigned) and the designated peer listening port for better readability.

## File Structure
- **config_file.py:**  
  Contains the seed node configurations (IP addresses and ports).

- **seed.py:**  
  Implements seed node functionality:
  - Accepts peer registrations.
  - Maintains a Peer List (PL).
  - Sends the peer list to new peers.
  - Processes dead node messages and removes dead peers from the list.

- **peer.py:**  
  Implements peer node functionality:
  - Connects to seed nodes and registers itself.
  - Obtains and processes peer lists.
  - Establishes connections with other peers.
  - Broadcasts gossip messages.
  - Monitors liveness via heartbeat (using system ping).
  - Logs detailed connection information, including ephemeral and designated ports.

- **main.py:**  
  Bootstraps the network by:
  - Starting multiple seed nodes.
  - Starting multiple peer nodes.
  - Connecting peers to seeds and other peers.
  - Simulating a peer going offline (intentionally closing the peer on port 8000) to test dead node detection.

## Requirements
- Python 3.x
- A system with the `ping` command available (adjust the ping command parameters in the code if necessary, especially on Windows).

## Running the Assignment
1. **Clone the repository:**
    ```bash
    git clone https://github.com/sujayv16/Computer_Network_Assign1.git
    ```
2. **Navigate to the repository directory:**
    ```bash
    cd Computer_Network_Assign1
    ```
3. **Run the main file:**
    ```bash
    python main.py
    ```
4. **Examine the logs:**  
   Log files for seed nodes (e.g., `logfile_seed_6000.txt`) and peer nodes (e.g., `logfile_peer_8000.txt`) will be generated. These logs include detailed information about connections (with both ephemeral and designated ports) and the progress of the gossip messages.

## Testing
- You can simulate multiple nodes on the same machine by using different ports.
- The code is designed to work in a distributed setting as well. Adjust the configuration in `config_file.py` if running on different machines.

## Additional Notes
- **Intentional Node Failure:**  
  The code intentionally closes the socket for the peer on port 8000 after a set time period to simulate a node failure. This triggers the dead node detection and reporting mechanism.
- **Enhanced Logging:**  
  Ephemeral ports (assigned by the OS) and designated ports (the peer’s listening port) are both logged to help with debugging and clarity.
- **Message Numbering:**  
  Gossip messages are numbered starting from 1 to enhance readability.

## Contact
For any questions or issues regarding this assignment, please contact:
- **Viswanadhapalli Sujay (b22cs063)**
- **Aiswarya (b22cs28)**
