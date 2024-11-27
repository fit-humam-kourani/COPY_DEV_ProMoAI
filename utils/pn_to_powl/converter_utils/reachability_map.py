from collections import deque, defaultdict
from itertools import combinations

import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util
import re

from pm4py.objects.petri_net.utils.reachability_graph import marking_flow_petri
from pm4py.objects.transition_system import obj as ts

from utils.pn_to_powl.converter_utils.subnet_creation import collect_subnet_transitions


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


def get_simplified_reachability_graph(net: PetriNet):
    # graph = {node: set() for node in set(net.places).union(net.transitions)}  # Initialize with all nodes as keys
    graph = {node: set() for node in net.transitions}
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


# def add_reachable(out_trans, res):
#     # post = pn_util.post_set(out_trans)
#     # new_nodes = post.difference(res)
#     # if len(new_nodes) > 0:
#     #     res.update(new_nodes)
#     #     for node in new_nodes:
#     #         add_reachable(node, res)
#     queue = deque()
#     queue.append(out_trans)
#     while queue:
#         node = queue.popleft()
#         if node not in res:
#             res.add(node)
#             successors = pn_util.post_set(node)
#             queue.extend(successors)


# def get_reachable_transitions_from_marking_branch(branch_start, f_state, transition_map):
#     reachable_transitions = set()
#     queue = deque()
#     queue.append(branch_start)
#     while queue:
#         next_elm = queue.popleft()
#         pn_transition = transition_map[next_elm]
#         reachable_transitions.add(pn_transition)
#         state = next_elm.to_state
#         if state is not f_state:
#             successors = state.outgoing
#             queue.extend(successors)
#
#     return reachable_transitions


def get_reachable_transitions_from_marking_to_another(im: Marking, fm: Marking, map_states, transition_map, simplified_reachability):
    """
    Returns all transitions that lie on some path from the initial marking (im) to the final marking (fm).
    """

    if simplified_reachability:
        if len(im) != 1 or len(fm) != 1:
            # This should not happen for loops as we preprocess to merge the places
            return set()
        start_place = list(im.keys())[0]
        end_place = list(fm.keys())[0]
        return collect_subnet_transitions(start_place, end_place)

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


def find_reachable_transitions_per_petri_transition(re_gr, transition_map):
    """
    For each Petri net transition, find all other Petri net transitions that are reachable from it
    based on the reachability graph.

    Args:
        re_gr (ts.TransitionSystem): The reachability graph.
        transition_map (dict): Mapping from reachability graph transitions to Petri net transitions.

    Returns:
        dict: A dictionary where keys are Petri net transitions and values are sets of reachable Petri net transitions.
    """

    petri_to_reach = defaultdict(set)
    for reach_tr, petri_tr in transition_map.items():
        petri_to_reach[petri_tr].add(reach_tr)

    petri_reachable = defaultdict(set)
    ts_reachable = defaultdict(set)

    reach_tr_reachable_cache = {}

    for petri_tr, reach_tr_set in petri_to_reach.items():
        reachable_petri = set()

        for reach_tr in reach_tr_set:
            if reach_tr in reach_tr_reachable_cache:
                # Use cached results
                reachable_petri.update(reach_tr_reachable_cache[reach_tr])
                continue

            # Perform BFS starting from the target state of the current reach_tr
            start_state = reach_tr.to_state
            queue = deque(start_state.outgoing)
            visited_reach_tr = set()
            local_reachable_petri = set()

            while queue:
                current_tr = queue.popleft()
                if current_tr not in visited_reach_tr:
                    visited_reach_tr.add(current_tr)
                    mapped_petri_tr = transition_map.get(current_tr)
                    if mapped_petri_tr:
                        local_reachable_petri.add(mapped_petri_tr)
                    # Enqueue successors
                    queue.extend(current_tr.to_state.outgoing)

            # Cache the reachable Petri transitions for the current reach_tr
            reach_tr_reachable_cache[reach_tr] = local_reachable_petri

            # Update the reachable Petri transitions for the current Petri transition
            reachable_petri.update(local_reachable_petri)
            ts_reachable[reach_tr] = local_reachable_petri

        reachable_petri.add(petri_tr)
        petri_reachable[petri_tr] = reachable_petri

    return ts_reachable


# def can_transition_be_reachable(A, B, reachable_transitions_dict):
#     """
#     Determines if transition A can be reached from transition B.
#
#     Parameters:
#     - A: The transition to check reachability for.
#     - B: The transition from which reachability is checked.
#     - reachable_transitions_dict: A dictionary mapping each transition to the set of transitions reachable from it.
#
#     Returns:
#     - True if A is reachable from B, False otherwise.
#     """
#     return A in reachable_transitions_dict.get(B, set())


def transitions_reachable_from_each_other(t1, t2, transition_map, reachable_ts_transitions_dict, simplified_reachability):

    if simplified_reachability:
        # in the simplified graph, transitions of a partial order cannot follow each other; only transitions
        # in a loop can follow each other
        return t1 in reachable_ts_transitions_dict[t2] and t2 in reachable_ts_transitions_dict[t1]
    else:
        ts_1 = {t for t in transition_map.keys() if transition_map[t] == t1}
        ts_2 = {t for t in transition_map.keys() if transition_map[t] == t2}
        for t in ts_1:
            if t2 not in reachable_ts_transitions_dict[t]:
                return False
        for t in ts_2:
            if t1 not in reachable_ts_transitions_dict[t]:
                return False

    return True


def can_transitions_be_on_same_path(reachable_ts_transitions_dict, transition_map, t1, t2):
    """
    Determines whether two Petri net transitions can be on the same path
    """
    if False:
        if t1 in reachable_ts_transitions_dict[t2] or t2 in reachable_ts_transitions_dict[t1]:
            return True
    else:
        for t_ts in reachable_ts_transitions_dict.keys():
            if transition_map[t_ts] == t1:
                if t2 in reachable_ts_transitions_dict[t_ts]:
                    return True
            elif transition_map[t_ts] == t2:
                if t1 in reachable_ts_transitions_dict[t_ts]:
                    return True

    return False
