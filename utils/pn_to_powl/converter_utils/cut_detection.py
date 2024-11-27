from collections import defaultdict, deque
from copy import copy
from itertools import combinations

import pm4py
from pm4py.objects.petri_net.utils.reachability_graph import construct_reachability_graph, marking_flow_petri
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util

from utils.pn_to_powl.converter_utils.reachability_map import get_reachable_transitions_from_marking_branch, \
    get_reachable_transitions_from_marking_to_another, find_reachable_transitions_per_petri_transition, \
    is_transition_always_reachable, can_transitions_be_on_same_path
from utils.pn_to_powl.converter_utils.subnet_creation import pn_transition_to_powl, \
    clone_place, add_arc_from_to, remove_arc


def mine_base_case(net: PetriNet):
    # A base case has exactly one transition and two places (start and end)
    if len(net.transitions) == 1:
        if len(net.arcs) == 2 == len(net.places):
            activity = list(net.transitions)[0]
            powl_transition = pn_transition_to_powl(activity)
            return powl_transition
    return None


def mine_self_loop(net: PetriNet, start_places: set[PetriNet.Place], end_places: set[PetriNet.Place]):
    # A base case has exactly one transition and two places (start and end)
    if len(start_places) == len(end_places) == 1:
        start_place = list(start_places)[0]
        end_place = list(end_places)[0]
        if start_place == end_place:
            print("NET: ", net)
            print("start_place: ", start_place)
            print("end_place: ", end_place)
            place = start_place
            place_copy = clone_place(net, place, {})
            redo = copy(net.transitions)

            out_arcs = place.out_arcs
            for arc in list(out_arcs):
                target = arc.target
                remove_arc(arc, net)
                add_arc_from_to(place_copy, target, net)

            do_transition = PetriNet.Transition(f"silent_do_{place.name}", None)
            do = set()
            do.add(do_transition)
            net.transitions.add(do_transition)
            add_arc_from_to(place, do_transition, net)
            add_arc_from_to(do_transition, place_copy, net)
            return do, redo, {place}, {place_copy}

    return None


def mine_loop(net: PetriNet, im: Marking, fm: Marking, map_states, reachable_pn_transitions_dict, reachable_ts_transitions_dict, transition_map):
    redo_subnet_transitions = get_reachable_transitions_from_marking_to_another(fm, im, map_states, transition_map)

    if len(redo_subnet_transitions) == 0:
        return None, None

    do_subnet_transitions = get_reachable_transitions_from_marking_to_another(im, fm, map_states, transition_map)

    if do_subnet_transitions & redo_subnet_transitions:
        raise Exception("Loop is detected but the do and redo parts are not disjoint!")

    if net.transitions != (do_subnet_transitions | redo_subnet_transitions):
        raise Exception("Something went wrong!", net.transitions, do_subnet_transitions, redo_subnet_transitions)

    return do_subnet_transitions, redo_subnet_transitions
    # Start and end places must have both incoming and outgoing arcs
    # start_place = list(start_places)[0]
    # end_place = list(end_places)[0]
    # start_has_incoming = len(start_place.in_arcs) > 0
    # start_has_outgoing = len(start_place.out_arcs) > 0
    # end_has_incoming = len(end_place.in_arcs) > 0
    # end_has_outgoing = len(end_place.out_arcs) > 0

    # if (start_has_incoming and start_has_outgoing and
    #         end_has_incoming and end_has_outgoing and start_place != end_place):
    #     do_subnet_transitions = collect_subnet_transitions(start_place, end_place)
    #     redo_subnet_transitions = collect_subnet_transitions(end_place, start_place)
    #     if len(do_subnet_transitions.intersection(redo_subnet_transitions)) > 0:
    #         raise Exception("Not a WF-net!")
    #     return do_subnet_transitions, redo_subnet_transitions
    # else:
    #     return None, None


def mine_xor(net, im, fm, reachable_pn_transitions_dict, reachable_ts_transitions_dict, transition_map):
    choice_branches = [[t] for t in net.transitions]
    # i_state = map_states[im]
    # f_state = map_states[fm]
    for t1, t2 in combinations(net.transitions, 2):
        if can_transitions_be_on_same_path(reachable_pn_transitions_dict, t1, t2):
            new_branch = {t1, t2}
            choice_branches = combine_partitions(new_branch, choice_branches)

    # merged_branches = combine_partitions()
    # while choice_branches:
    #     branch = choice_branches.pop(0)
    #     merged = False
    #     for i, other_branch in enumerate(merged_branches):
    #         if branch & other_branch:  # Check for intersection
    #             merged_branches[i] = other_branch | branch  # Merge branches
    #             merged = True
    #             break
    #     if not merged:
    #         merged_branches.append(branch)
    print("merged_branches")
    print(choice_branches)
    return choice_branches


def mine_partial_order(net, start_places, end_places, reachable_pn_transitions_dict, reachable_ts_transitions_dict, transition_map):
    # partition_map = defaultdict(list)
    #
    # for key, value_set in reachable_transitions_dict.items():
    #     partition_map[frozenset(value_set)].append(key)
    # partitions = list(partition_map.values())
    #
    # print("partitions")
    partitions = [[t] for t in net.transitions]
    print(partitions)

    # nodes_not_grouped = [group[0] for group in partitions if len(group) == 1]
    # places_not_grouped = [node for node in nodes_not_grouped if isinstance(node, PetriNet.Place)]
    #
    # candidate_xor_start = set()
    # # candidate_xor_end = set()
    #
    # for place in places_not_grouped:
    #     in_size = len(place.in_arcs)
    #     out_size = len(place.out_arcs)
    #     if in_size == 0 and place not in start_places:
    #         raise Exception(f"A place with no incoming arcs! {place}")
    #     if out_size == 0 and place not in end_places:
    #         raise Exception(f"A place with no outgoing arcs! {place}")
    #     # if in_size > 1 and out_size == 1:
    #     #     candidate_xor_end.add(place)
    #     if out_size > 1 and in_size == 1:
    #         candidate_xor_start.add(place)
    #
    # for place_xor_split in candidate_xor_start:
    #     xor_branches = []
    #     for start_transition in pn_util.post_set(place_xor_split):
    #         new_branch = set()
    #         # add_reachable(start_transition, new_branch)
    #
    #         # if end_place not in new_branch:
    #         #     raise Exception(f"Not a WF-net! End place not reachable from {start_transition}!")
    #         xor_branches.append(new_branch)
    #
    #     # extract the set of nodes that are not present in EVERY branch
    #     union_of_branches = set().union(*xor_branches)
    #     intersection_of_branches = set.intersection(*xor_branches)
    #     not_in_every_branch = union_of_branches - intersection_of_branches
    #     if len(not_in_every_branch) == 1:
    #         raise Exception("This is not possible")
    #     elif len(not_in_every_branch) > 1:
    #         partitions = combine_partitions(not_in_every_branch, partitions)

    # transition_partitions = []
    # for group in partitions:
    #     t_group = [node for node in group if isinstance(node, PetriNet.Transition)]
    #     if len(t_group) > 0:
    #         transition_partitions.append(t_group)

    parent = list(range(len(partitions)))  # Each partition is initially its own parent

    def find(i):
        """Find the root parent of partition i with path compression."""
        if parent[i] != i:
            parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        """Union the sets containing partitions i and j."""
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_j] = root_i  # Merge j into i

    # Step 3: Iterate through all pairs of transitions to determine incompatibility
    for t1, t2 in combinations(net.transitions, 2):
        ts_1 = {t for t in transition_map.keys() if transition_map[t] == t1}
        ts_2 = {t for t in transition_map.keys() if transition_map[t] == t2}

        if (is_transition_always_reachable(ts_1, t2, reachable_ts_transitions_dict)
            and is_transition_always_reachable(ts_2, t1, reachable_ts_transitions_dict)) \
                or not can_transitions_be_on_same_path(reachable_pn_transitions_dict, t1, t2):
            # Find the indices of the partitions containing t1 and t2
            p1 = next(idx for idx, p in enumerate(partitions) if t1 in p)
            p2 = next(idx for idx, p in enumerate(partitions) if t2 in p)
            # Union the partitions if they are not already in the same set
            union(p1, p2)

    # Step 4: Merge partitions based on the Union-Find structure
    merged_partitions = defaultdict(list)
    for idx, partition in enumerate(partitions):
        root = find(idx)
        merged_partitions[root].extend(partition)

    partitions = list(merged_partitions.values())

    # Optional: If you want to remove duplicates after merging
    partitions = [list(set(part)) for part in partitions]

    print("final p:")
    print(partitions)

    return partitions


def combine_partitions(input_set, partitions):
    """
    Combines groups of partitions if they share elements in the given input set.

    Args:
    - input_set (set): The set of elements to check for intersection.
    - partitions (list of lists): The current list of partitions to combine.

    Returns:
    - list of lists: Updated partitions after combining groups that share elements.
    """
    combined_partitions = []
    new_combined_group = set()

    for partition in partitions:
        partition_set = set(partition)
        # Check if there is an intersection with the input_set
        if partition_set & input_set:
            new_combined_group.update(partition_set)
        else:
            combined_partitions.append(partition)

    # Combine all visited sets into one partition
    if new_combined_group:
        combined_partitions.append(list(new_combined_group))

    return combined_partitions


def mine_sequence(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place, reachability_graph):
    """
    Determine if the Petri net represents a sequence by identifying connection points.

    Parameters:
    - net: PetriNet
    - start_place: Place (start of the sequence)
    - end_place: Place (end of the sequence)

    Returns:
    - Tuple (is_sequence_detected: bool, connection_points: List[PetriNet.Place])
      - is_sequence_detected: True if a sequence is detected, False otherwise.
      - connection_points: List of connection places if a sequence is detected; otherwise, [start_place, end_place].
    """
    # reachability_map_places = {key: value for key, value in reachability_graph.items() if isinstance(key, PetriNet.Place)}

    sorted_nodes = sorted(reachability_graph.keys(), key=lambda k: len(reachability_graph[k]), reverse=True)
    connection_points = []

    for i in range(len(sorted_nodes)):
        p = sorted_nodes[i]
        if isinstance(p, PetriNet.Place):
            if set(reachability_graph[p]) == set(sorted_nodes[i:]):
                if all(p in reachability_graph[q] for q in sorted_nodes[:i]):
                    if not any(p in reachability_graph[q] for q in sorted_nodes[i + 1:]):
                        connection_points.append(p)

    if len(connection_points) >= 2:
        if start_place not in connection_points:
            raise Exception("Start place not detected as a connection_point!")
        if end_place not in connection_points:
            raise Exception("End place not detected as a connection_point!")

    return connection_points, [p for p in sorted_nodes if isinstance(p, PetriNet.Place)]


def find_states_with_transition(transition_map, petri_transition):
    return {tr for tr, pt in transition_map.items() if pt == petri_transition}
