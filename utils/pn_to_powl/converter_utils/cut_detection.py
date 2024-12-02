from copy import copy
from itertools import combinations
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util
from utils.pn_to_powl.converter_utils.reachability_graph import transitions_always_reachable_from_each_other, \
    can_transitions_be_on_same_path, get_reachable_transitions_from_marking_to_another
from utils.pn_to_powl.converter_utils.weak_reachability import transitions_reachable_from_each_other, \
    get_reachable_transitions_from_place_to_another
from utils.pn_to_powl.converter_utils.subnet_creation import pn_transition_to_powl, \
    clone_place, add_arc_from_to


def mine_base_case(net: PetriNet):
    if len(net.transitions) == 1:
        if len(net.arcs) == 2 == len(net.places):
            activity = list(net.transitions)[0]
            powl_transition = pn_transition_to_powl(activity)
            return powl_transition
    return None


def mine_self_loop(net: PetriNet, start_places: set[PetriNet.Place], end_places: set[PetriNet.Place]):
    if len(start_places) == len(end_places) == 1:
        start_place = list(start_places)[0]
        end_place = list(end_places)[0]
        if start_place == end_place:
            place = start_place
            place_copy = clone_place(net, place, {})
            redo = copy(net.transitions)
            out_arcs = place.out_arcs
            for arc in list(out_arcs):
                target = arc.target
                pn_util.remove_arc(net, arc)
                add_arc_from_to(place_copy, target, net)
            do_transition = PetriNet.Transition(f"silent_do_{place.name}", None)
            do = set()
            do.add(do_transition)
            net.transitions.add(do_transition)
            add_arc_from_to(place, do_transition, net)
            add_arc_from_to(do_transition, place_copy, net)
            return do, redo, {place}, {place_copy}

    return None


def mine_loop(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place, im: Marking, fm: Marking,
              map_states, transition_map, simplified_reachability):
    if simplified_reachability:

        redo_subnet_transitions = get_reachable_transitions_from_place_to_another(end_place, start_place)

        if len(redo_subnet_transitions) == 0:
            return None, None

        do_subnet_transitions = get_reachable_transitions_from_place_to_another(start_place, end_place)

    else:

        redo_subnet_transitions = get_reachable_transitions_from_marking_to_another(fm, im, map_states, transition_map)

        if len(redo_subnet_transitions) == 0:
            return None, None

        do_subnet_transitions = get_reachable_transitions_from_marking_to_another(im, fm, map_states, transition_map)

    if len(do_subnet_transitions) == 0:
        raise Exception("This should not be possible!")

    if do_subnet_transitions & redo_subnet_transitions:
        # This could happen if we have ->(..., Loop)
        return None, None

    if net.transitions != (do_subnet_transitions | redo_subnet_transitions):
        raise Exception("Something went wrong!")

    # A loop is detected: the set of transitions is partitioned into two disjoint, non-empty subsets (do and redo)
    return do_subnet_transitions, redo_subnet_transitions


def mine_xor(net: PetriNet, start_place: PetriNet.Place, reachability_map, transition_map, simplified_reachability):
    choice_branches = [{t} for t in net.transitions]

    if simplified_reachability:
        # for start_transition in pn_util.post_set(start_place):
        #     new_branch = {node for node in reachability_map[start_transition]
        #                   if isinstance(node, PetriNet.Transition)}
        #     choice_branches = __combine_partitions(new_branch, choice_branches)
        for t1, t2 in combinations(net.transitions, 2):
            if t1 in reachability_map[t2] or t2 in reachability_map[t1]:
                new_branch = {t1, t2}
                choice_branches = __combine_partitions(new_branch, choice_branches)
    else:
        for t1, t2 in combinations(net.transitions, 2):
            if can_transitions_be_on_same_path(t1, t2, transition_map, reachability_map):
                new_branch = {t1, t2}
                choice_branches = __combine_partitions(new_branch, choice_branches)

    if net.transitions != set().union(*choice_branches):
        raise Exception("This should not happen!")

    return choice_branches


def mine_partial_order(net, reachability_map, transition_map, simplified_reachability):
    partitions = [{t} for t in net.transitions]

    for t1, t2 in combinations(net.transitions, 2):

        if simplified_reachability:
            merge = transitions_reachable_from_each_other(t1,
                                                          t2,
                                                          reachability_map)

        else:
            merge = transitions_always_reachable_from_each_other(t1,
                                                                 t2,
                                                                 transition_map,
                                                                 reachability_map) \
                    or not can_transitions_be_on_same_path(t1,
                                                           t2,
                                                           transition_map,
                                                           reachability_map)

        if merge:
            partitions = __combine_partitions({t1, t2}, partitions)

    if simplified_reachability:
        for place in net.places:
            out_size = len(place.out_arcs)
            if out_size > 1:
                xor_branches = []
                for start_transition in pn_util.post_set(place):
                    new_branch = {node for node in reachability_map[start_transition]
                                  if isinstance(node, PetriNet.Transition)}
                    xor_branches.append(new_branch)
                union_of_branches = set().union(*xor_branches)
                intersection_of_branches = set.intersection(*xor_branches)
                not_in_every_branch = union_of_branches - intersection_of_branches
                if len(not_in_every_branch) > 1:
                    partitions = __combine_partitions(not_in_every_branch, partitions)

    return partitions


def __combine_partitions(transitions_to_group_together: set[PetriNet.Transition],
                         partitions: list[set[PetriNet.Transition]]):
    combined_partitions = []
    new_combined_group = set()

    for partition_set in partitions:

        if partition_set & transitions_to_group_together:
            new_combined_group.update(partition_set)
        else:
            combined_partitions.append(partition_set)

    if new_combined_group:
        combined_partitions.append(new_combined_group)

    return combined_partitions
