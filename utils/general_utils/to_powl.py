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
    if t1 == t2:
        return False
    if len(pn_util.pre_set(t1)) == 0 or len(pn_util.post_set(t1)) == 0 or len(pn_util.pre_set(t2)) == 0 or len(
            pn_util.post_set(t2)) == 0:
        return False
    pre_pre = set()
    post_post = set()
    for p in pn_util.pre_set(t1):
        pre_pre = set.union(pre_pre, pn_util.pre_set(p))
        if len(pn_util.post_set(p)) > 1 or t1 not in pn_util.post_set(p):
            return False
    for p in pn_util.post_set(t1):
        post_post = set.union(post_post, pn_util.post_set(p))
        if len(pn_util.pre_set(p)) > 1 or t1 not in pn_util.pre_set(p):
            return False
    for p in pn_util.pre_set(t2):
        pre_pre = set.union(pre_pre, pn_util.pre_set(p))
        if len(pn_util.post_set(p)) > 1 or t2 not in pn_util.post_set(p):
            return False
    for p in pn_util.post_set(t2):
        post_post = set.union(post_post, pn_util.post_set(p))
        if len(pn_util.pre_set(p)) > 1 or t2 not in pn_util.pre_set(p):
            return False
    for p in set.union(pn_util.pre_set(t1), pn_util.pre_set(t2)):
        for t in pre_pre:
            if t not in pn_util.pre_set(p):
                return False
    for p in set.union(pn_util.post_set(t1), pn_util.post_set(t2)):
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


def sequence_requirement(t1, t2):
    if t1 == t2:
        return False
    if len(pn_util.pre_set(t2)) == 0:
        return False
    for p in pn_util.post_set(t1):
        if len(pn_util.pre_set(p)) != 1 or len(pn_util.post_set(p)) != 1:
            return False
        if t1 not in pn_util.pre_set(p):
            return False
        if t2 not in pn_util.post_set(p):
            return False
    for p in pn_util.pre_set(t2):
        if len(pn_util.pre_set(p)) != 1 or len(pn_util.post_set(p)) != 1:
            return False
        if t1 not in pn_util.pre_set(p):
            return False
        if t2 not in pn_util.post_set(p):
            return False
    return True


def binary_sequence_detection(net, t2powl_node):
    c1 = None
    c2 = None
    for t1, t2 in itertools.product(net.transitions, net.transitions):
        if sequence_requirement(t1, t2):
            c1 = t1
            c2 = t2
            break
    if c1 is not None and c2 is not None:
        # Create a StrictPartialOrder POWL node with c1 and c2, and add an order from c1 to c2
        n1 = t2powl_node[c1]
        n2 = t2powl_node[c2]
        if isinstance(n2, SilentTransition):
            new_powl_node = n1
        elif isinstance(n1, SilentTransition):
            new_powl_node = n2
        else:
            new_powl_node = StrictPartialOrder(nodes=[n1, n2])
            new_powl_node.order.add_edge(n1, n2)
        t_new = PetriNet.Transition(TRANSITION_PREFIX + str(datetime.datetime.now()))
        t_new.label = None
        # Map t_new to the new POWL node
        t2powl_node[t_new] = new_powl_node
        net.transitions.add(t_new)
        # Connect t_new in the net where c1 and c2 were
        for a in c1.in_arcs:
            pn_util.add_arc_from_to(a.source, t_new, net)
        for a in c2.out_arcs:
            pn_util.add_arc_from_to(t_new, a.target, net)
        # Remove the intermediate place between c1 and c2
        for p in pn_util.post_set(c1):
            pn_util.remove_place(net, p)
        # Remove the old transitions c1 and c2
        pn_util.remove_transition(net, c1)
        pn_util.remove_transition(net, c2)
        return net
    return None


def __group_blocks_internal(net, t2powl_node, parameters=None):
    if parameters is None:
        parameters = {}

    # Attempt to reduce the net by detecting patterns and grouping them
    # The functions will modify the net and t2powl_node mapping
    if binary_choice_detection(net, t2powl_node) is not None:
        return True
    elif binary_sequence_detection(net, t2powl_node) is not None:
        return True
    elif binary_concurrency_detection(net, t2powl_node) is not None:
        return True
    elif binary_loop_detection(net, t2powl_node) is not None:
        return True
    else:
        return False


def __insert_dummy_invisibles(net, t2powl_node, im, fm, ini_places, parameters=None):
    if parameters is None:
        parameters = {}

    places = list(net.places)

    for p in places:
        if p.name in ini_places:
            if p not in im and p not in fm:
                source_trans = [x.source for x in p.in_arcs]
                target_trans = [x.target for x in p.out_arcs]

                pn_util.remove_place(net, p)
                source_p = PetriNet.Place(str(uuid.uuid4()))
                target_p = PetriNet.Place(str(uuid.uuid4()))
                skip = PetriNet.Transition(str(uuid.uuid4()))
                net.places.add(source_p)
                net.places.add(target_p)
                net.transitions.add(skip)

                pn_util.add_arc_from_to(source_p, skip, net)
                pn_util.add_arc_from_to(skip, target_p, net)

                for t in source_trans:
                    pn_util.add_arc_from_to(t, source_p, net)
                for t in target_trans:
                    pn_util.add_arc_from_to(target_p, t, net)

                # Add the new silent transition to t2powl_node
                t2powl_node[skip] = SilentTransition()

def group_blocks_in_net(net, t2powl_node, parameters=None):
    """
    Groups the blocks in the Petri net

    Parameters
    --------------
    net
        Petri net
    t2powl_node
        Mapping from transitions to POWL nodes
    parameters
        Parameters of the algorithm

    Returns
    --------------
    grouped_net
        Petri net (blocks are grouped according to the algorithm)
    """
    if parameters is None:
        parameters = {}

    from pm4py.algo.analysis.workflow_net import algorithm as wf_eval

    if not wf_eval.apply(net):
        raise ValueError('The Petri net provided is not a WF-net')

    ini_places = set(x.name for x in net.places)

    while len(net.transitions) > 1:
        im = Marking({p: 1 for p in net.places if len(p.in_arcs) == 0})
        fm = Marking({p: 1 for p in net.places if len(p.out_arcs) == 0})

        if len(im) != 1 and len(fm) != 1:
            break

        if __group_blocks_internal(net, t2powl_node, parameters):
            continue
        else:
            __insert_dummy_invisibles(net, t2powl_node, im, fm, ini_places, parameters)
            if __group_blocks_internal(net, t2powl_node, parameters):
                continue
            else:
                break

    return net


def extract_partial_order_from_net(net, t2powl_node):
    '''
    Extracts the partial order from the Petri net structure for the remaining transitions.
    Removes silent transitions by linking their predecessors to their successors until no silent transitions remain.
    Returns a StrictPartialOrder POWL model with nodes and order.

    Parameters:
    - net: The Petri net containing the remaining transitions
    - t2powl_node: Mapping from Petri net transitions to POWL model nodes

    Returns:
    - powl_model: A StrictPartialOrder POWL model representing the partial order over the transitions
    '''
    # Initialize the set of nodes (POWL nodes corresponding to transitions)
    nodes = set()
    # Initialize the set of order relations (edges) between nodes
    order_relations = set()

    # Map transitions to POWL nodes
    for t in net.transitions:
        # Collect the POWL nodes corresponding to the transitions
        nodes.add(t2powl_node[t])

    # For each place in the net, extract immediate causality relations
    for p in net.places:
        # Get the transitions in the pre-set (transitions leading to this place)
        pre_transitions = set()
        for a in p.in_arcs:
            t = a.source
            if isinstance(t, PetriNet.Transition):
                pre_transitions.add(t)
        # Get the transitions in the post-set (transitions that this place leads to)
        post_transitions = set()
        for a in p.out_arcs:
            t = a.target
            if isinstance(t, PetriNet.Transition):
                post_transitions.add(t)
        # For each pair of transitions (t1, t2) such that t1 in pre-set(p) and t2 in post-set(p)
        for t1 in pre_transitions:
            for t2 in post_transitions:
                # Add an order relation from t1 to t2
                source = t2powl_node[t1]
                target = t2powl_node[t2]
                order_relations.add((source, target))

    # Now, build the directed graph
    import networkx as nx
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(order_relations)

    # Remove silent transitions and connect their predecessors to their successors
    silent_transitions_exist = True
    while silent_transitions_exist:
        silent_transitions_exist = False
        # Find all SilentTransition nodes
        silent_nodes = [n for n in G.nodes if isinstance(n, SilentTransition)]
        if silent_nodes:
            silent_transitions_exist = True
            for n in silent_nodes:
                # Get predecessors and successors of the silent node
                preds = list(G.predecessors(n))
                succs = list(G.successors(n))
                # For each predecessor and successor, add an edge from pred to succ
                for p in preds:
                    for s in succs:
                        if p != s:
                            G.add_edge(p, s)
                # Remove the silent node from the graph
                G.remove_node(n)
        else:
            silent_transitions_exist = False

    # After removing silent transitions, update the nodes set
    nodes = set(G.nodes())

    # Now, check for cycles in the relations to ensure it's a partial order
    if not nx.is_directed_acyclic_graph(G):
        # If there are cycles, we need to remove edges to break cycles
        # For simplicity, we can remove one edge from each cycle
        try:
            # Find cycles in the graph
            cycles = list(nx.simple_cycles(G))
            for cycle in cycles:
                if len(cycle) > 1:
                    # Remove an edge to break the cycle
                    G.remove_edge(cycle[0], cycle[1])
                else:
                    # Self-loop, remove it
                    G.remove_edge(cycle[0], cycle[0])
        except Exception as e:
            # In case of any error, we can raise an exception or proceed
            pass

    # Now G should be acyclic
    # Reconstruct order_relations from G
    order_relations = set(G.edges())

    # Create the StrictPartialOrder POWL model
    powl_model = StrictPartialOrder(nodes=nodes)
    # Add the order relations
    for source, target in order_relations:
        powl_model.order.add_edge(source, target)

    return powl_model


def apply(net, im, fm, parameters=None):
    """
    Transforms a WF-net to a POWL model

    Parameters
    -------------
    net
        Petri net
    im
        Initial marking
    fm
        Final marking

    Returns
    -------------
    powl_model
        POWL model
    """
    if parameters is None:
        parameters = {}

    debug = exec_utils.get_param_value(Parameters.DEBUG, parameters, False)
    # There is no fold for POWLs, so we do not try that.

    # Do the deepcopy here
    net = deepcopy(net)
    # Initialize the mapping from transitions to POWL nodes
    t2powl_node = {}
    for t in net.transitions:
        if t.label is None:
            # Silent transitions are represented by SilentTransition nodes
            t2powl_node[t] = SilentTransition()
        else:
            # Labeled transitions are represented by POWLTransition nodes with the label
            t2powl_node[t] = POWLTransition(label=t.label)

    grouped_net = group_blocks_in_net(net, t2powl_node, parameters=parameters)

    if debug:
        from pm4py.visualization.petri_net import visualizer as pn_viz
        pn_viz.view(pn_viz.apply(grouped_net, parameters={"format": "svg"}))
        return grouped_net
    else:
        if len(grouped_net.transitions) == 1:
            # If the net has been fully reduced to a single transition, return the corresponding POWL model
            t_final = list(grouped_net.transitions)[0]
            powl_model = t2powl_node[t_final]
            powl_model = powl_model.simplify()
            return powl_model
        else:
            # Extend the approach to incorporate partial orders between transitions
            # that could not have been handled by process trees.

            # Extract the partial order from the remaining net
            powl_model = extract_partial_order_from_net(grouped_net, t2powl_node)

            return powl_model