from collections import deque

import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from typing import Union, List, Dict, Set
from pm4py.objects.petri_net.utils import petri_utils as pn_util
from pm4py.objects.powl.obj import POWL, Transition, OperatorPOWL, Operator, StrictPartialOrder, SilentTransition, \
    Sequence

from utils.general_utils.to_powl_tests import test_loop, test_choice, test_choice2


def id_generator():
    count = 1
    while True:
        yield f"id{count}"
        count += 1


# Example usage
id_gen = id_generator()


def translate_petri_to_powl(net: PetriNet, initial_marking: Marking, final_marking: Marking) -> POWL:
    """
    Convert a Petri net to a POWL model.

    Parameters:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking

    Returns:
    - POWL model
    """
    print("Transitions: ", net.transitions)
    print("Places: ", net.places)
    print("Arcs: ", net.arcs)
    validate_petri_net(net, initial_marking, final_marking)
    preprocess_net(net, initial_marking, final_marking)

    # Identify start and end places
    start_places = [p for p in net.places if p in initial_marking]
    end_places = [p for p in net.places if p in final_marking]

    if len(start_places) != 1 or len(end_places) != 1:
        raise NotImplementedError("Only Petri nets with a single start and end place are supported.")

    start_place = start_places[0]
    end_place = end_places[0]

    # Check for base case
    if is_base_case(net, start_place, end_place):
        print("Base case detected")
        return translate_single_transition(net, start_place, end_place)

    # Check for Sequence split
    seq_points, sorted_places, reachability_map = is_sequence(net, start_place, end_place)
    # we need at least three connection poits for a sequence: start_place, cut_point, end_place
    if len(seq_points) > 2:
        print("Seq detected")
        return translate_seq(net, seq_points, sorted_places, reachability_map)

    # Check for XOR split
    choice_branches = is_xor(net, start_place, end_place)
    if choice_branches and len(choice_branches) > 1:
        print("XOR detected")
        return translate_xor(net, start_place, end_place, choice_branches)

    if is_loop(net, start_place, end_place):
        print("Loop detected")
        return translate_loop(net, start_place, end_place)

    # Placeholder for other cases (e.g., AND splits, loops)
    raise NotImplementedError("This type of Petri net structure is not yet implemented.")


def validate_petri_net(net: PetriNet, initial_marking: Marking, final_marking: Marking):
    """
    Validate the Petri net according to the specified rules.

    Raises:
    - PetriNetException if any validation fails.
    """
    from pm4py.algo.analysis.workflow_net import algorithm as wf_eval

    if not wf_eval.apply(net):
        raise ValueError('The Petri net provided is not a WF-net')

    # 1. Initial and final markings must each contain exactly one place
    if len(initial_marking) != 1:
        raise Exception(f"Initial marking must consist of exactly one place: {initial_marking}")
    if len(final_marking) != 1:
        raise Exception(f"Final marking must consist of exactly one place: {final_marking}")

    # 2. Initial marking must be the same as all places with no incoming arcs
    places_no_incoming = [p for p in net.places if not p.in_arcs]
    if set(places_no_incoming) != set(initial_marking.keys()):
        raise Exception(f"Initial marking must match all places with no incoming arcs. {places_no_incoming}")

    # 3. Final marking must be the same as all places with no outgoing arcs
    places_no_outgoing = [p for p in net.places if not p.out_arcs]
    if set(places_no_outgoing) != set(final_marking.keys()):
        raise Exception(f"Final marking must match all places with no outgoing arcs. {places_no_outgoing}")


def preprocess_net(net: PetriNet, initial_marking: Marking, final_marking: Marking):
    """
    Preprocess the Petri net by removing silent transitions at the start and end.

    Modifies the net and markings in place.
    """
    if len(net.transitions) < 2:
        return
    # Preprocess start: remove p -> silent_transition -> p2
    start_places = [p for p in net.places if p in initial_marking]
    if len(start_places) == 1:
        start_place = start_places[0]
        successors = list(pn_util.post_set(start_place))
        if len(successors) == 1:
            transition = successors[0]
            if is_silent(transition):
                # Assuming silent transitions have some identifiable property
                next_places = list(pn_util.post_set(transition))
                if len(next_places) == 1:
                    p2 = next_places[0]
                    # Remove the transition and the start_place
                    pn_util.remove_transition(net, transition)
                    pn_util.remove_place(net, start_place)
                    # Update initial_marking to p2
                    initial_marking.clear()
                    initial_marking[p2] = 1
                    start_preprocessed = True
                    print(f"Preprocessed start: Removed {start_place} and {transition}, set {p2} as initial marking.")

    # Preprocess end: remove p3 -> silent_transition -> p4
    end_places = [p for p in net.places if p in final_marking]
    if len(end_places) == 1:
        end_place = end_places[0]
        predecessors = list(pn_util.pre_set(end_place))
        if len(predecessors) == 1:
            transition = predecessors[0]
            if is_silent(transition):
                prev_places = list(pn_util.pre_set(transition))
                if len(prev_places) == 1:
                    p3 = prev_places[0]
                    # Remove the transition and the end_place
                    pn_util.remove_transition(net, transition)
                    pn_util.remove_place(net, end_place)
                    # Update final_marking to p3
                    final_marking.clear()
                    final_marking[p3] = 1
                    end_preprocessed = True
                    print(f"Preprocessed end: Removed {p3} and {transition}, set {p3} as final marking.")


def is_silent(transition) -> bool:
    """
    Determine if a transition is silent.

    This function should be implemented based on how silent transitions are represented.
    For example, they might have a specific label like 'tau' or a property flag.
    """
    return transition.label is None


def is_base_case(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place) -> bool:
    """
    Determine if the Petri net is a base case: single transition between start and end.

    Returns:
    - Boolean
    """
    # A base case has exactly one transition and two places (start and end)
    return len(net.transitions) == 1 and len(net.places) == 2


def translate_single_transition(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place) -> Transition:
    """
    Translate a base case Petri net to a POWL Transition.

    Returns:
    - POWL Transition object
    """
    transition = list(net.transitions)[0]
    label = transition.label
    if label:
        return Transition(label=label)
    else:
        return SilentTransition()


def translate_seq(net, connection_points, ordered_places, reachability_map):
    powl_sub_models = []
    index = 0
    # excluded last place, which must be a connection point (otherwise, exception would have been thrown earlier)
    for i in range(len(ordered_places) - 1):
        p = ordered_places[i]
        if p in connection_points:
            node_map = {}

            index = index + 1
            sub_net = PetriNet(f"Subnet_{index}")
            sub_start_place = PetriNet.Place(name=f"{p.name}_subnet{index}",
                                             in_arcs=set(),
                                             out_arcs=p.out_arcs)
            node_map[p] = sub_start_place
            sub_net.places.add(sub_start_place)
            subnet_initial_marking = Marking()
            subnet_final_marking = Marking()
            subnet_initial_marking[sub_start_place] = 1
            p_next = None
            # add all next places until reaching a connection point
            for j in range(i + 1, len(ordered_places)):
                p_next = ordered_places[j]
                if p_next in connection_points:
                    cloned_place = PetriNet.Place(name=f"{p_next.name}_subnet{index}",
                                                  in_arcs=p_next.in_arcs,
                                                  out_arcs=set())
                    sub_net.places.add(cloned_place)
                    subnet_final_marking[cloned_place] = 1
                    node_map[p_next] = cloned_place
                    break
                else:
                    cloned_place = PetriNet.Place(name=f"{p_next.name}_subnet{index}",
                                                  in_arcs=p_next.in_arcs,
                                                  out_arcs=p_next.out_arcs)
                    sub_net.places.add(cloned_place)
                    node_map[p_next] = cloned_place

            # add transitions
            for t in net.transitions:
                if t in reachability_map[p] and t not in reachability_map[p_next]:
                    new_t = PetriNet.Transition(f"{t.name}_subnet{index}", t.label)
                    sub_net.transitions.add(new_t)
                    node_map[t] = new_t

            # add arcs
            for arc in net.arcs:
                source = arc.source
                target = arc.target
                if source in node_map.keys() and target in node_map.keys():
                    add_arc_from_to(node_map[source], node_map[target], sub_net)

            powl = translate_petri_to_powl(sub_net, subnet_initial_marking, subnet_final_marking)
            powl_sub_models.append(powl)

    return Sequence(nodes=powl_sub_models)


def is_sequence(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place):
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
    reachability_map = get_reachable_nodes_mapping(net)

    reachable_places_map = {key: value for key, value in reachability_map.items() if isinstance(key, PetriNet.Place)}

    sorted_places = sorted(reachable_places_map.keys(), key=lambda k: len(reachability_map[k]), reverse=True)
    connection_points = []

    for i in range(len(sorted_places)):
        p = sorted_places[i]
        if set(node for node in reachability_map[p] if isinstance(node, PetriNet.Place)) == set(sorted_places[i + 1:]):
            if all(p in reachability_map[q] for q in sorted_places[:i]):
                connection_points.append(p)

    if len(connection_points) >= 2:
        if start_place not in connection_points:
            raise Exception("Start place not detected as a connection_point!")
        if end_place not in connection_points:
            raise Exception("End place not detected as a connection_point!")

    return connection_points, sorted_places, reachability_map


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


def is_xor(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place):
    """
    Determine if the Petri net starts with an XOR split at start_place and ends with an XOR join at end_place.

    Parameters:
    - net: PetriNet
    - start_place: Place (start of the XOR split)
    - end_place: Place (end of the XOR join)

    Returns:
    - Boolean indicating whether an XOR structure exists.
    """

    len_start_incoming = len(start_place.in_arcs)
    len_start_outgoing = len(start_place.out_arcs)
    len_end_incoming = len(end_place.in_arcs)
    len_end_outgoing = len(end_place.out_arcs)

    if len_start_outgoing <= 1:
        # print("Not an XOR split: start_place has <=1 outgoing transitions.")
        return None

    if len_end_incoming <= 1:
        # print("Not an XOR join: end_place has <=1 incoming transitions.")
        return None

    if len_start_incoming > 0 or len_end_outgoing > 0:
        # print("Not an XOR: possible loop!")
        return None

    choice_branches = []
    # Connectivity between split and join
    for start_transition in pn_util.post_set(start_place):
        new_branch = set()
        new_branch.update([start_transition])
        add_reachable(start_transition, new_branch)
        if end_place not in new_branch:
            raise Exception(f"Not a WF-net! End place not reachable from {start_transition}!")
        new_branch.remove(end_place)
        choice_branches.append(new_branch)

    # Combine overlapping branches
    merged_branches = []
    while choice_branches:
        branch = choice_branches.pop(0)  # Take the first branch
        merged = False
        for i, other_branch in enumerate(merged_branches):
            if branch & other_branch:  # Check for intersection
                merged_branches[i] = other_branch | branch  # Merge branches
                merged = True
                break
        if not merged:
            merged_branches.append(branch)

    return merged_branches


def add_reachable(out_trans, res):
    post = pn_util.post_set(out_trans)
    new_nodes = post.difference(res)
    if len(new_nodes) > 0:
        res.update(new_nodes)
        for node in new_nodes:
            add_reachable(node, res)


def create_sub_powl_model(net, branch, start_place, end_place):
    subnet = create_subnet(net, branch, start_place, end_place)
    return translate_petri_to_powl(
        subnet['net'],
        subnet['initial_marking'],
        subnet['final_marking']
    )


def translate_xor(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place, choice_branches):
    """
    Translate an XOR split and join in the Petri net into a POWL OperatorPOWL with Operator.XOR.

    Parameters:
    - net: PetriNet (original net)
    - start_place: Place (start of the XOR split)
    - end_place: Place (final end place of the net)

    Returns:
    - OperatorPOWL object representing the XOR operator with translated subnets.
    """
    children = []
    for branch in choice_branches:
        child_powl = create_sub_powl_model(net, branch, start_place, end_place)
        children.append(child_powl)
    xor_operator = OperatorPOWL(operator=Operator.XOR, children=children)
    return xor_operator


def is_loop(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place):
    """
    Determine if the Petri net represents a loop structure.

    A loop is characterized by the start and end places having both incoming and outgoing arcs.
    """
    # Start and end places must have both incoming and outgoing arcs
    start_has_incoming = len(start_place.in_arcs) > 0
    start_has_outgoing = len(start_place.out_arcs) > 0
    end_has_incoming = len(end_place.in_arcs) > 0
    end_has_outgoing = len(end_place.out_arcs) > 0

    return (start_has_incoming and start_has_outgoing and
            end_has_incoming and end_has_outgoing and start_place != end_place)


def translate_loop(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place) -> OperatorPOWL:
    """
    Translate a loop structure in the Petri net into a POWL OperatorPOWL with Operator.LOOP.
    """
    do_subnet_nodes = collect_subnet_nodes(net, start_place, end_place)
    redo_subnet_nodes = collect_subnet_nodes(net, end_place, start_place)

    if len(do_subnet_nodes.intersection(redo_subnet_nodes)) > 0:
        raise Exception("Not a WF-net!")

    do_powl = create_sub_powl_model(net, do_subnet_nodes, start_place, end_place)
    redo_powl = create_sub_powl_model(net, redo_subnet_nodes, end_place, start_place)
    loop_operator = OperatorPOWL(operator=Operator.LOOP, children=[do_powl, redo_powl])

    return loop_operator


def collect_subnet_nodes(net: PetriNet, source_place: PetriNet.Place, target_place: PetriNet.Place) -> Set[
    Union[PetriNet.Place, PetriNet.Transition]]:
    """
    Collect all nodes in the subnet from source_place to target_place.
    """
    visited = set()
    queue = deque()
    queue.append(source_place)
    while queue:
        node = queue.popleft()
        if node not in visited:
            visited.add(node)
            if node == target_place:
                continue
            successors = pn_util.post_set(node)
            queue.extend(successors)
    visited.remove(source_place)
    visited.remove(target_place)
    return visited


def create_subnet(net: PetriNet, subnet_nodes: Set[Union[PetriNet.Place, PetriNet.Transition]],
                  start_place: PetriNet.Place, end_place: PetriNet.Place) -> Dict:
    """
    Create a subnet Petri net from the given nodes.
    """
    subnet_net = PetriNet(f"Subnet_{next(id_gen)}")

    # Introduce fresh start and end places
    fresh_start_p = PetriNet.Place(f"fresh_start_{next(id_gen)}")
    subnet_net.places.add(fresh_start_p)
    subnet_initial_marking = Marking()
    subnet_initial_marking[fresh_start_p] = 1

    fresh_end_p = PetriNet.Place(f"fresh_end_{next(id_gen)}")
    subnet_net.places.add(fresh_end_p)
    subnet_final_marking = Marking()
    subnet_final_marking[fresh_end_p] = 1

    node_map = {}
    for node in subnet_nodes:
        if isinstance(node, PetriNet.Place):
            cloned_place = PetriNet.Place(f"{node.name}_cloned")
            subnet_net.places.add(cloned_place)
            node_map[node] = cloned_place
        elif isinstance(node, PetriNet.Transition):
            cloned_trans = PetriNet.Transition(f"{node.name}_cloned", node.label)
            subnet_net.transitions.add(cloned_trans)
            node_map[node] = cloned_trans

    # Add arcs within the subnet
    for arc in net.arcs:
        if arc.source in subnet_nodes and arc.target in subnet_nodes:
            cloned_source = node_map[arc.source]
            cloned_target = node_map[arc.target]
            add_arc_from_to(cloned_source, cloned_target, subnet_net)

    # Connect fresh start and end places
    for t in pn_util.post_set(start_place).intersection(subnet_nodes):
        add_arc_from_to(fresh_start_p, node_map[t], subnet_net)
    for t in pn_util.pre_set(end_place).intersection(subnet_nodes):
        add_arc_from_to(node_map[t], fresh_end_p, subnet_net)

    return {
        'net': subnet_net,
        'initial_marking': subnet_initial_marking,
        'final_marking': subnet_final_marking
    }


def add_arc_from_to(source: Union[PetriNet.Place, PetriNet.Transition],
                    target: Union[PetriNet.Transition, PetriNet.Place], net: PetriNet):
    """
    Add an arc from source to target in the Petri net.

    Parameters:
    - source: Place or Transition
    - target: Transition or Place
    - net: PetriNet
    """
    arc = PetriNet.Arc(source, target)
    net.arcs.add(arc)
    source.out_arcs.add(arc)
    target.in_arcs.add(arc)


if __name__ == "__main__":
    # net, initial_marking, final_marking = test_choice2()
    net, initial_marking, final_marking = test_loop()

    powl_model = translate_petri_to_powl(net, initial_marking, final_marking)
    pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")
    pm4py.view_powl(powl_model, format="SVG")
