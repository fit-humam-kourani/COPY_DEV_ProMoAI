from collections import deque

import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util
import re

from pm4py.objects.petri_net.utils.reachability_graph import marking_flow_petri
from pm4py.objects.transition_system import obj as ts


# def get_reachable_up_to(start, candidate_xor_end):
#     reachable = set()
#     queue = deque()
#     queue.append(start)
#     while queue:
#         node = queue.popleft()
#         if node not in reachable:
#             reachable.add(node)
#             if node in candidate_xor_end:
#                 continue
#             successors = pn_util.post_set(node)
#             queue.extend(successors)
#     return reachable


# def get_reachable_till_end(start):
#     reachable = set()
#     queue = deque()
#     queue.append(start)
#     while queue:
#         node = queue.popleft()
#         if node not in reachable:
#             reachable.add(node)
#             successors = pn_util.post_set(node)
#             queue.extend(successors)
#     return reachable


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


# def get_reachable_nodes_mapping(net: PetriNet):
#     """
#     Compute the reachability of each place in the Petri net.
#
#     Parameters:
#     - net: PetriNet
#
#     Returns:
#     - Dictionary where each key is a place and the value is a set of places reachable from it.
#     """
#     reachability = {}
#     for place in net.places:
#         res = set()
#         add_reachable(place, res)
#         reachability[place] = res
#     return reachability


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


def get_reachable_transitions_from_marking_branch(branch_start, transition_map):
    reachable_transitions = set()
    queue = deque()
    queue.append(branch_start)
    while queue:
        next_elm = queue.popleft()
        pn_transition = transition_map[next_elm]
        if pn_transition not in reachable_transitions:
            reachable_transitions.add(pn_transition)
            state = next_elm.to_state
            successors = state.outgoing
            queue.extend(successors)
    return reachable_transitions


def get_reachable_transitions_from_marking_to_another(im: Marking, fm: Marking, map_states, transition_map):
    """
    Returns all transitions that lie on some path from the initial marking (im) to the final marking (fm).
    """
    i_state = map_states[im]
    f_state = map_states[fm]

    reachable_transitions = set()

    # Step 1: Backward BFS to find all states that can reach fm
    reachable_states_from_fm = set()
    backward_queue = deque([f_state])
    while backward_queue:
        current_state = backward_queue.popleft()
        if current_state not in reachable_states_from_fm:
            reachable_states_from_fm.add(current_state)
            # Assuming each state has incoming transitions
            for incoming_transition in current_state.incoming:
                from_state = incoming_transition.from_state
                backward_queue.append(from_state)

    # Step 2: Forward BFS from im, only considering transitions leading to reachable states
    forward_queue = deque(i_state.outgoing)
    while forward_queue:
        transition = forward_queue.popleft()
        if transition not in reachable_transitions:
            to_state = transition.to_state
            # Only consider this transition if to_state can reach fm
            if to_state in reachable_states_from_fm:
                reachable_transitions.add(transition)
                if to_state != f_state:
                    forward_queue.extend(to_state.outgoing)

    return {transition_map[elm] for elm in reachable_transitions}


def add_arc_from_to_ts(t_map, pn_transition, fr, to, tsys, data=None):
    tran = pm4py.objects.transition_system.obj.TransitionSystem.Transition(repr(pn_transition), fr, to, data)
    tsys.transitions.add(tran)
    fr.outgoing.add(tran)
    to.incoming.add(tran)
    t_map[tran] = pn_transition
    return t_map


def generate_reachability_graph(net, im):
    incoming_transitions, outgoing_transitions, eventually_enabled = marking_flow_petri(net, im)

    re_gr = ts.TransitionSystem()

    map_states = {}
    transition_map = {}
    for s in incoming_transitions:
        map_states[s] = ts.TransitionSystem.State(staterep(repr(s)))
        re_gr.states.add(map_states[s])

    for s1 in outgoing_transitions:
        for t in outgoing_transitions[s1]:
            s2 = outgoing_transitions[s1][t]
            add_arc_from_to_ts(transition_map, t, map_states[s1], map_states[s2], re_gr)

    return re_gr, map_states, transition_map


def staterep(name):
    return re.sub(r'\W+', '', name)
