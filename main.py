# main.py
# Import the Seed and Peer classes from their respective modules,
# along with other required modules.
from seed import Seed
from peer import Peer
import time
import random
import config_file  # Contains seed node configuration (IP and port info)

# Retrieve seed node information from the config file.
seed_info = config_file.seed_info

def main():
    # -----------------------------------------------------------------------
    # Start Seed Nodes
    # -----------------------------------------------------------------------
    seed_list = []  # List to store seed node instances.
    for key, (ip, port) in seed_info.items():
        # Inform that the seed node is starting.
        print(f"Starting seed node {key} at {ip}:{port} .....")
        # Create a new Seed instance with the given IP and port.
        s = Seed(ip, port)
        # Start the seed node (this begins listening for connections).
        s.start()
        # Add the seed node to the list for later reference.
        seed_list.append(s)
    
    # Allow a short delay to ensure that all seed nodes are up and running.
    time.sleep(2)

    # -----------------------------------------------------------------------
    # Start Peer Nodes
    # -----------------------------------------------------------------------
    peer_list = []  # List to store peer node instances.
    num_seeds = len(seed_list)  # Total number of seed nodes.
    
    # Create 5 peer nodes with ports ranging from 8000 to 8003.
    for port in range(8000, 8003):
        # Create a new Peer instance with localhost as IP and the given port.
        p = Peer("127.0.0.1", port)
        # Start the peer (this begins listening for incoming connections and starts gossiping).
        p.start()
        
        # -------------------------------------------------------------------
        # Connect to Seed Nodes:
        # Each peer must connect to at least ⌊(n/2)⌋ + 1 seeds.
        # -------------------------------------------------------------------
        num_seed_connections = (num_seeds // 2) + 1
        # Randomly sample the required number of seed nodes from the available list.
        sampled_seeds = random.sample(seed_list, num_seed_connections)
        for seed in sampled_seeds:
            # Connect the peer to each sampled seed node.
            p.connect_to_seed(seed.host, seed.port)
        
        # Allow some time for the peer to receive the peer list from the seed nodes.
        time.sleep(1)
        
        # -------------------------------------------------------------------
        # Connect to Other Peers:
        # After obtaining peer lists from seeds, select some peers to connect to.
        # For simulation purposes, a simple random selection is used.
        # (In a full implementation, a power-law weighted selection could be applied.)
        # -------------------------------------------------------------------
        candidate_peers = list(p.peers)
        # Remove self from the candidate list (if the peer's own entry is present).
        candidate_peers = [peer for peer in candidate_peers if not (peer[0] == "127.0.0.1" and peer[1] == port)]
        # Limit the number of connections to a maximum of 4 or the number of available candidates.
        num_connections = min(4, len(candidate_peers))
        if num_connections > 0:
            # Randomly select peers from the candidate list.
            selected_peers = random.sample(candidate_peers, num_connections)
            for peer_ip, peer_port in selected_peers:
                # Connect to each selected peer.
                p.connect_to_peer(peer_ip, peer_port)
        
        # Add the current peer to the peer_list for future reference.
        peer_list.append(p)
        # Short delay between starting each peer.
        time.sleep(1)
    
    # -----------------------------------------------------------------------
    # Simulate Network Operation
    # -----------------------------------------------------------------------
    # Let the network run for 30 seconds to allow gossiping and connections.
    time.sleep(30)
    
    # -----------------------------------------------------------------------
    # Simulate a Peer Failure
    # -----------------------------------------------------------------------
    # To test the dead node detection mechanism, simulate a peer going offline
    # by closing the socket of the first peer in the peer_list.
    if peer_list:
        peer_list[0].close_socket()
    
    # -----------------------------------------------------------------------
    # Keep the Main Thread Alive
    # -----------------------------------------------------------------------
    # This loop keeps the main thread alive so that daemon threads (for gossip,
    # heartbeats, etc.) continue to run.
    while True:
        time.sleep(10)

# Run the main function if this script is executed directly.
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down.")
