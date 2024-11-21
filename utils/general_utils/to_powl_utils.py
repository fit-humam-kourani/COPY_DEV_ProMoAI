import datetime
import itertools
import uuid
from copy import deepcopy
from enum import Enum

from pm4py.objects.petri_net.utils import petri_utils as pn_util
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.powl.obj import OperatorPOWL, StrictPartialOrder, Transition as POWLTransition, SilentTransition
from pm4py.objects.process_tree.obj import Operator
from pm4py.util import exec_utils

TRANSITION_PREFIX = str(uuid.uuid4())


class Parameters(Enum):
    DEBUG = "debug"


def generate_label_for_transition(t):
    return 'tau' if t.label is None else '\'' + t.label + '\'' if not t.name.startswith(
        TRANSITION_PREFIX) else t.label


def loop_requirement(t1, t2):
    if t1 == t2:
        return False
    for p in pn_util.pre_set(t2):
        if len(pn_util.pre_set(p)) != 1:
            return False
        if t1 not in pn_util.pre_set(p):
            return False
    for p in pn_util.post_set(t2):
        if len(pn_util.post_set(p)) != 1:
            return False
        if t1 not in pn_util.post_set(p):
            return False
    for p in pn_util.pre_set(t1):
        if len(pn_util.post_set(p)) != 1:
            return False
        if t1 not in pn_util.post_set(p):
            return False
        if t2 not in pn_util.pre_set(p):
            return False
    for p in pn_util.post_set(t1):
        if len(pn_util.pre_set(p)) != 1:
            return False
        if t1 not in pn_util.pre_set(p):
            return False
        if t2 not in pn_util.post_set(p):
            return False
    return True


def binary_loop_detection(net, t2powl_node):
    c1 = None
    c2 = None
    for t1, t2 in itertools.product(net.transitions, net.transitions):
        if loop_requirement(t1, t2):
            c1 = t1
            c2 = t2
            break
    if c1 is not None and c2 is not None:
        # Create new POWL node representing the loop operator over t2powl_node[c1] and t2powl_node[c2]
        new_powl_node = OperatorPOWL(operator=Operator.LOOP, children=[t2powl_node[c1], t2powl_node[c2]])
        # Create new transition t_new to replace c1 and c2 in the net
        t_new = PetriNet.Transition(TRANSITION_PREFIX + str(datetime.datetime.now()))
        t_new.label = None  # No label, as it's a structural node
        # Map t_new to the new POWL node
        new_powl_node = new_powl_node.simplify()
        t2powl_node[t_new] = new_powl_node
        net.transitions.add(t_new)
        # Connect t_new in the net where c1 was
        for a in c1.in_arcs:
            pn_util.add_arc_from_to(a.source, t_new, net)
        for a in c1.out_arcs:
            pn_util.add_arc_from_to(t_new, a.target, net)
        # Remove the old transitions c1 and c2
        pn_util.remove_transition(net, c1)
        pn_util.remove_transition(net, c2)
        return net
    return None


def concurrent_requirement(t1, t2):
    if t1 == t2:  # check if transitions different
        return False
    if len(pn_util.pre_set(t1)) == 0 or len(pn_util.post_set(t1)) == 0 or len(pn_util.pre_set(t2)) == 0 or len(
            pn_util.post_set(t2)) == 0:  # not possible in WF-net, just checking...
        return False
    pre_pre = set()
    post_post = set()
    for p in pn_util.pre_set(t1):  # check if t1 is unique post of its preset
        if len(pn_util.post_set(p)) > 1 or t1 not in pn_util.post_set(p):
            return False

    for p in pn_util.post_set(t1):  # check if t1 is unique pre of its postset
        post_post = set.union(post_post, pn_util.post_set(p))
        if len(pn_util.pre_set(p)) > 1 or t1 not in pn_util.pre_set(p):
            return False
    for p in pn_util.pre_set(t2):  # check if t2 is unique post of its preset
        pre_pre = set.union(pre_pre, pn_util.pre_set(p))
        if len(pn_util.post_set(p)) > 1 or t2 not in pn_util.post_set(p):
            return False
    for p in pn_util.post_set(t2):  # check if t2 is unique pre of its postset
        post_post = set.union(post_post, pn_util.post_set(p))
        if len(pn_util.pre_set(p)) > 1 or t2 not in pn_util.pre_set(p):
            return False
    for p in set.union(pn_util.pre_set(t1), pn_util.pre_set(t2)):  # check if presets synchronize
        for t in pre_pre:
            if t not in pn_util.pre_set(p):
                return False
    for p in set.union(pn_util.post_set(t1), pn_util.post_set(t2)):  # check if postsets synchronize
        for t in post_post:
            if t not in pn_util.post_set(p):
                return False
    return True


def binary_concurrency_detection(net, t2powl_node):
    c1 = None
    c2 = None
    for t1, t2 in itertools.product(net.transitions, net.transitions):
        if concurrent_requirement(t1, t2):
            c1 = t1
            c2 = t2
            break
    if c1 is not None and c2 is not None:
        # Create a StrictPartialOrder POWL node with c1 and c2 as nodes
        new_powl_node = StrictPartialOrder(nodes=[t2powl_node[c1], t2powl_node[c2]])
        print("Conc: ", t2powl_node[c1], ", ", t2powl_node[c2])
        # No order between c1 and c2 means they can occur concurrently
        t_new = PetriNet.Transition(TRANSITION_PREFIX + str(datetime.datetime.now()))
        t_new.label = None
        # Map t_new to the new POWL node
        t2powl_node[t_new] = new_powl_node
        net.transitions.add(t_new)
        # Merge the pre-sets and post-sets of c1 and c2 for t_new
        pres = set(a.source for a in c1.in_arcs).union(set(a.source for a in c2.in_arcs))
        posts = set(a.target for a in c1.out_arcs).union(set(a.target for a in c2.out_arcs))
        for p in pres:
            pn_util.add_arc_from_to(p, t_new, net)
        for p in posts:
            pn_util.add_arc_from_to(t_new, p, net)
        # Remove the old transitions c1 and c2
        pn_util.remove_transition(net, c1)
        pn_util.remove_transition(net, c2)
        return net
    return None



def choice_requirement(t1, t2):
    return t1 != t2 and pn_util.pre_set(t1) == pn_util.pre_set(t2) and pn_util.post_set(t1) == pn_util.post_set(
        t2) and len(pn_util.pre_set(t1)) > 0 and len(
        pn_util.post_set(t1)) > 0


def binary_choice_detection(net, t2powl_node):
    c1 = None
    c2 = None
    for t1, t2 in itertools.product(net.transitions, net.transitions):
        if choice_requirement(t1, t2):
            c1 = t1
            c2 = t2
            break
    if c1 is not None and c2 is not None:
        # Create an OperatorPOWL node with XOR operator for choice between c1 and c2
        new_powl_node = OperatorPOWL(operator=Operator.XOR, children=[t2powl_node[c1], t2powl_node[c2]])
        t_new = PetriNet.Transition(TRANSITION_PREFIX + str(datetime.datetime.now()))
        t_new.label = None
        # Map t_new to the new POWL node
        new_powl_node = new_powl_node.simplify()
        t2powl_node[t_new] = new_powl_node
        net.transitions.add(t_new)
        # Connect t_new in the net where c1 and c2 were
        for a in c1.in_arcs:
            pn_util.add_arc_from_to(a.source, t_new, net)
        for a in c1.out_arcs:
            pn_util.add_arc_from_to(t_new, a.target, net)
        # Remove the old transitions c1 and c2
        pn_util.remove_transition(net, c1)
        pn_util.remove_transition(net, c2)
        return net
    return None











# def extract_partial_order_from_net(net, t2powl_node):
#     '''
#     Extracts the partial order from the Petri net structure for the remaining transitions.
#     Removes silent transitions by linking their predecessors to their successors until no silent transitions remain.
#     Returns a StrictPartialOrder POWL model with nodes and order.
#
#     Parameters:
#     - net: The Petri net containing the remaining transitions
#     - t2powl_node: Mapping from Petri net transitions to POWL model nodes
#
#     Returns:
#     - powl_model: A StrictPartialOrder POWL model representing the partial order over the transitions
#     '''
#     # Initialize the set of nodes (POWL nodes corresponding to transitions)
#     nodes = set()
#     # Initialize the set of order relations (edges) between nodes
#     order_relations = set()
#
#     # Map transitions to POWL nodes
#     for t in net.transitions:
#         # Collect the POWL nodes corresponding to the transitions
#         nodes.add(t2powl_node[t])
#
#     # For each place in the net, extract immediate causality relations
#     for p in net.places:
#         # Get the transitions in the pre-set (transitions leading to this place)
#         pre_transitions = set()
#         for a in p.in_arcs:
#             t = a.source
#             if isinstance(t, PetriNet.Transition):
#                 pre_transitions.add(t)
#         # Get the transitions in the post-set (transitions that this place leads to)
#         post_transitions = set()
#         for a in p.out_arcs:
#             t = a.target
#             if isinstance(t, PetriNet.Transition):
#                 post_transitions.add(t)
#         # For each pair of transitions (t1, t2) such that t1 in pre-set(p) and t2 in post-set(p)
#         for t1 in pre_transitions:
#             for t2 in post_transitions:
#                 # Add an order relation from t1 to t2
#                 source = t2powl_node[t1]
#                 target = t2powl_node[t2]
#                 order_relations.add((source, target))
#
#     # Now, build the directed graph
#     import networkx as nx
#     G = nx.DiGraph()
#     G.add_nodes_from(nodes)
#     G.add_edges_from(order_relations)
#
#     # Remove silent transitions and connect their predecessors to their successors
#     silent_transitions_exist = True
#     while silent_transitions_exist:
#         silent_transitions_exist = False
#         # Find all SilentTransition nodes
#         silent_nodes = [n for n in G.nodes if isinstance(n, SilentTransition)]
#         if silent_nodes:
#             silent_transitions_exist = True
#             for n in silent_nodes:
#                 # Get predecessors and successors of the silent node
#                 preds = list(G.predecessors(n))
#                 succs = list(G.successors(n))
#                 # For each predecessor and successor, add an edge from pred to succ
#                 for p in preds:
#                     for s in succs:
#                         if p != s:
#                             G.add_edge(p, s)
#                 # Remove the silent node from the graph
#                 G.remove_node(n)
#         else:
#             silent_transitions_exist = False
#
#     # After removing silent transitions, update the nodes set
#     nodes = set(G.nodes())
#
#     # Now, check for cycles in the relations to ensure it's a partial order
#     if not nx.is_directed_acyclic_graph(G):
#         # If there are cycles, we need to remove edges to break cycles
#         # For simplicity, we can remove one edge from each cycle
#         try:
#             # Find cycles in the graph
#             cycles = list(nx.simple_cycles(G))
#             for cycle in cycles:
#                 if len(cycle) > 1:
#                     # Remove an edge to break the cycle
#                     G.remove_edge(cycle[0], cycle[1])
#                 else:
#                     # Self-loop, remove it
#                     G.remove_edge(cycle[0], cycle[0])
#         except Exception as e:
#             # In case of any error, we can raise an exception or proceed
#             pass
#
#     # Now G should be acyclic
#     # Reconstruct order_relations from G
#     order_relations = set(G.edges())
#
#     # Create the StrictPartialOrder POWL model
#     powl_model = StrictPartialOrder(nodes=nodes)
#     # Add the order relations
#     for source, target in order_relations:
#         powl_model.order.add_edge(source, target)
#
#     return powl_model

