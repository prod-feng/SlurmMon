from slurm.client import SlurmClient
from slurm.parsers import (
        parse_node_details,
        parse_nodes,
)

class NodeService:
    def __init__(self, client=None):
        self.client = client or SlurmClient()

    def list_nodes(self):
        output = self.client.nodes()
        return parse_nodes(output)

    def drain(self, node: str, reason: str):
        if not reason.strip():
            raise ValueError("A drain reason is required.")

        return self.client.drain_node(node, reason.strip())

    def resume(self, node: str):
        return self.client.resume_node(node)

    def get_node_details(self, node_name):
        output = self.client.node_details(
             node_name
         )

        return parse_node_details(output)

