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
from to_powl_utils import *


# def sequence_requirement(t1, t2):
#     if t1 == t2:
#         return False
#     if len(pn_util.pre_set(t2)) == 0:
#         return False
#     for p in pn_util.post_set(t1):
#         if len(pn_util.pre_set(p)) != 1 or len(pn_util.post_set(p)) != 1:
#             return False
#         if t1 not in pn_util.pre_set(p):
#             return False
#         if t2 not in pn_util.post_set(p):
#             return False
#     for p in pn_util.pre_set(t2):
#         if len(pn_util.pre_set(p)) != 1 or len(pn_util.post_set(p)) != 1:
#             return False
#         if t1 not in pn_util.pre_set(p):
#             return False
#         if t2 not in pn_util.post_set(p):  # redundant check, just to be sure...
#             return False
#     return True
def sequence_requirement(t1, t2):
    if t1 == t2:
        return False
    if len(pn_util.pre_set(t2)) == 0:
        return False
    for p in pn_util.post_set(t1):
        if len(pn_util.pre_set(p)) == 1 and len(pn_util.post_set(p)) == 1:
            if t2 in pn_util.post_set(p):
                return True
    return False


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
            print("Seq: ", n1, ", ", n2)
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
        for p in pn_util.pre_set(c2):
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
    elif binary_loop_detection(net, t2powl_node) is not None:
        return True
    elif binary_concurrency_detection(net, t2powl_node) is not None:
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
            # powl_model = powl_model.simplify()
            return powl_model
        else:
            # raise Exception('Converting the WF-net into POWL failed!')
            # powl_model = extract_partial_order_from_net(grouped_net, t2powl_node)
            #
            nodes = [t2powl_node[node] for node in list(grouped_net.transitions)]
            powl_model = StrictPartialOrder(nodes)
            # powl_model = powl_model.simplify()
            return powl_model


import pm4py

from pm4py.objects.powl.obj import (
    OperatorPOWL,
    StrictPartialOrder,
    Transition as POWLTransition,
    SilentTransition,
)
from pm4py.objects.process_tree.obj import Operator
from pm4py.visualization.powl import visualizer as powl_viz

# Step 1: Define POWL Transitions
transition_A = POWLTransition(label='A')
transition_B = POWLTransition(label='B')
transition_C = POWLTransition(label='C')
transition_D = POWLTransition(label='D')
transition_D1 = POWLTransition(label='D1')
transition_D2 = POWLTransition(label='D2')
transition_E = POWLTransition(label='E')
transition_F = POWLTransition(label='F')

# Step 2: Create Nested Partial Orders
PO2 = StrictPartialOrder(nodes=[transition_A, transition_B])
PO3 = StrictPartialOrder(nodes=[transition_C, transition_D, transition_D1, transition_D2])
PO3.order.add_edge(transition_D, transition_D1)
# PO3.order.add_edge(transition_D, transition_D2)
PO3.order.add_edge(transition_C, transition_D2)
PO4 = StrictPartialOrder(nodes=[transition_E, transition_F])

# Step 3: Create Exclusive Choice (XOR1) and Loop (LOOP1)
XOR1 = OperatorPOWL(operator=Operator.XOR, children=[PO2, SilentTransition()])
LOOP1 = OperatorPOWL(operator=Operator.LOOP, children=[PO3, SilentTransition()])

# Step 4: Create Top-Level Partial Order (PO1)
PO1 = StrictPartialOrder(nodes=[XOR1, LOOP1, PO4])

# Step 5: Visualize the POWL Model
pm4py.view_powl(PO1, format="svg")

pn, im, fm = pm4py.convert_to_petri_net(PO1)

P02 = apply(pn, im, fm)
pm4py.view_powl(P02, format="svg")
