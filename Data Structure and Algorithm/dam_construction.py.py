class Graph:
    def __init__(self, num_vertices):
        # Initialize the graph with the given number of vertices (states and junctions)
        self.num_vertices = num_vertices
        # Create an adjacency list for each vertex
        self.adjacency_list = [[] for _ in range(num_vertices)]
    
    def add_edge(self, src, dest, weight):
        # Ensure the source and destination are valid nodes
        if src < 0 or src >= self.num_vertices or dest < 0 or dest >= self.num_vertices:
            raise IndexError("Vertex index out of bound.")
        # Add an edge (flow of river), with weight, from source to destination
        self.adjacency_list[src].append((dest, weight))
    
    def get_edges(self, vertex):
        # Ensure the vertex is a valid vertex
        if vertex < 0 or vertex >= self.num_vertices:
            raise IndexError("vertex index out of bound.")
        # Return the list of edges for the given vertex
        return self.adjacency_list[vertex]

class Queue:
    def __init__(self):
        # Initialization of an empty queue
        self.queue = []
    
    def enqueue(self, item):
        # Appending an item at the end of the queue
        self.queue.append(item)
    
    def dequeue(self):
        # Removing and returning the item from the start of the queue

        if not self.is_empty():
            return self.queue.pop(0)
        else:
            raise IndexError("Dequeuing from the empty queue.")
    
    def is_empty(self):
        # Check if the queue is empty
        return len(self.queue) == 0

def read_graph(input_file):
    
    with open(input_file, 'r') as ifile:
        # Read river flow(edges) between nodes from the input file by splitting each line by '/'
        edges = [line.strip().split('/') for line in ifile]
    
    # Create a mapping for node names to location indexes
    location_map = {}
    location = 0
    
    # Pass 1: Build the nodes mapping
    for edge in edges:
        node1, node2, weight = edge[0].strip(), edge[1].strip(), int(edge[2].strip())

        if weight < 0:
            print(f"Error: {weight} between '{node1}' and '{node2}' is negative (Weight cannot be negative as river cannot flow in opposite direction). Exiting.")
            exit(1)
        
        # Map node names to locations
        if node1 not in location_map:
            location_map[node1] = location
            location += 1
        if node2 not in location_map:
            location_map[node2] = location
            location += 1
            
    # Create the graph of states and junctions
    graph = Graph(len(location_map))
    
    # Pass 2: add edges between nodes and assign weight to the edge
    for edge in edges:
        node1 = location_map[edge[0].strip()]
        node2 = location_map[edge[1].strip()]
        weight = int(edge[2].strip())
        
        # Add edges to the graph
        graph.add_edge(node1, node2, weight)
    
    return graph, location_map

def bfs_dam_locations(graph, flow_threshold):
    dam_locations = []
    visited = [False] * graph.num_vertices
    bfs_traversal = []  # To store the order of BFS traversal
    
    # Perform BFS for each unvisited node
    for start_node in range(graph.num_vertices):
        if not visited[start_node]:
            queue = Queue()
            queue.enqueue(start_node)
            visited[start_node] = True
            
            while not queue.is_empty():
                current_node = queue.dequeue()
                bfs_traversal.append(current_node)  # Tracking the order of node visit
                adjacent_node = graph.get_edges(current_node)

                # Calculating the total outgoing flow from the current node
                outgoing_flow = sum(weight for _, weight in adjacent_node)

                # Check the total outgoing flow against flow threshold
                if len(adjacent_node) > 1 and outgoing_flow >= flow_threshold:  
                    # Dam to be constructed at the node if total outgoing flow is more than the set flow threshold
                    dam_locations.append((current_node, outgoing_flow))  

                # Visit all unvisited adjacent_node
                for neighbour, weight in adjacent_node:
                    if not visited[neighbour]:
                        visited[neighbour] = True
                        queue.enqueue(neighbour)

    return dam_locations, bfs_traversal

def write_output(dam_locations, bfs_traversal, output_file, location_map):
    # Opening the output file
    with open(output_file, 'w', encoding='utf-8') as ofile:
        # Write BFS Traversal Output
        bfs_traversal_output = "BFS Traversal Output: " + " → ".join([name for idx in bfs_traversal for name, index in location_map.items() if index == idx])
        ofile.write(bfs_traversal_output + "\n")
        
        ofile.write("Dam constructed at Locations:\n")
        for idx, (node_index, flow) in enumerate(dam_locations):
            # Reverse lookup to get the original node name from index
            original_node_name = [name for name, index in location_map.items() if index == node_index][0]
            ofile.write(f"{idx + 1}. Node {original_node_name}:\n")  
            ofile.write(f"   Total outgoing flow = {flow}.\n")
            ofile.write(f"   {'Ideal location for a major dam due to high flow.' if flow > 300 else 'Suitable for moderate dam construction.'}\n")

if __name__ == "__main__":
    # Read the structure of river flow structure from input file
    river_flow_graph, location_map = read_graph("inputPS07.txt")
    flow_threshold = 250  # Flow threshold
    # Find dam locations using BFS
    dam_locations, bfs_traversal = bfs_dam_locations(river_flow_graph, flow_threshold)
    # Write the results to the output file
    write_output(dam_locations, bfs_traversal, "outputPS07.txt", location_map)
