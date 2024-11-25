from collections import deque
from pm4py.objects.petri_net.obj import PetriNet
from pm4py.objects.petri_net.utils import petri_utils as pn_util


def get_reachable_up_to(start, candidate_xor_end):
    reachable = set()
    queue = deque()
    queue.append(start)
    while queue:
        node = queue.popleft()
        if node not in reachable:
            reachable.add(node)
            if node in candidate_xor_end:
                continue
            successors = pn_util.post_set(node)
            queue.extend(successors)
    return reachable


def get_reachable_till_end(start):
    reachable = set()
    queue = deque()
    queue.append(start)
    while queue:
        node = queue.popleft()
        if node not in reachable:
            reachable.add(node)
            successors = pn_util.post_set(node)
            queue.extend(successors)
    return reachable


def get_reachability_graph(net: PetriNet):
    graph = {node: set() for node in set(net.places).union(net.transitions)}  # Initialize with all nodes as keys
    for start_node in graph.keys():
        reachable = set()
        queue = deque()
        queue.append(start_node)
        while queue:
            node = queue.popleft()
            if node not in reachable:
                reachable.add(node)
                successors = pn_util.post_set(node)
                queue.extend(successors)
        graph[start_node].update(reachable)
    return graph


def get_reachable_nodes_mapping(net: PetriNet):
    """
    Compute the reachability of each place in the Petri net.

    Parameters:
    - net: PetriNet

    Returns:
    - Dictionary where each key is a place and the value is a set of places reachable from it.
    """
    reachability = {}
    for place in net.places:
        res = set()
        add_reachable(place, res)
        reachability[place] = res
    return reachability


def add_reachable(out_trans, res):
    # post = pn_util.post_set(out_trans)
    # new_nodes = post.difference(res)
    # if len(new_nodes) > 0:
    #     res.update(new_nodes)
    #     for node in new_nodes:
    #         add_reachable(node, res)
    queue = deque()
    queue.append(out_trans)
    while queue:
        node = queue.popleft()
        if node not in res:
            res.add(node)
            successors = pn_util.post_set(node)
            queue.extend(successors)
