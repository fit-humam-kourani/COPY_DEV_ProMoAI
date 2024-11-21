from collections import deque

import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from typing import Union, List, Dict, Set
from pm4py.objects.petri_net.utils import petri_utils as pn_util
from pm4py.objects.powl.obj import POWL, Transition, OperatorPOWL, Operator, StrictPartialOrder, SilentTransition


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
        print("Base case:", net.transitions)
        return translate_single_transition(net, start_place, end_place)

    # Check for XOR split
    if is_xor(net, start_place, end_place):
        print("XOR:", net.transitions)
        return translate_xor(net, start_place, end_place)

    if is_loop(net, start_place, end_place):
        print("Loop detected:", net.transitions)
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
        print(initial_marking)
        raise Exception("Initial marking must consist of exactly one place.")
    if len(final_marking) != 1:
        raise Exception("Final marking must consist of exactly one place.")

    # 2. Initial marking must be the same as all places with no incoming arcs
    places_no_incoming = [p for p in net.places if not p.in_arcs]
    print(places_no_incoming)
    if set(places_no_incoming) != set(initial_marking.keys()):
        raise Exception("Initial marking must match all places with no incoming arcs.")

    # 3. Final marking must be the same as all places with no outgoing arcs
    places_no_outgoing = [p for p in net.places if not p.out_arcs]
    if set(places_no_outgoing) != set(final_marking.keys()):
        print(places_no_outgoing)
        print(final_marking.keys())
        raise Exception("Final marking must match all places with no outgoing arcs.")


def preprocess_net(net: PetriNet, initial_marking: Marking, final_marking: Marking):
    """
    Preprocess the Petri net by removing silent transitions at the start and end.

    Modifies the net and markings in place.
    """
    if len(net.transitions) < 2:
        return
    # Preprocess start: remove p -> silent_transition -> p2
    start_preprocessed = False
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
    end_preprocessed = False
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


def is_xor(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place) -> bool:
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
        print("Not an XOR split: start_place has <=1 outgoing transitions.")
        return False

    if len_end_incoming <= 1:
        print("Not an XOR join: end_place has <=1 incoming transitions.")
        return False

    if len_start_incoming > 0 or len_end_outgoing:
        print("Not an XOR: possible loop!")
        return False

    # Step 3: Verify that the number of outgoing transitions equals incoming transitions
    if len_start_outgoing != len_end_incoming:
        print("Mismatch in number of outgoing and incoming transitions.")
        return False

    # Optional: Further verification can be added here (e.g., connectivity between split and join)

    return True


def add_reachable(out_trans, res):
    post = pn_util.post_set(out_trans)
    new_nodes = post.difference(res)
    if len(new_nodes) > 0:
        res.update(new_nodes)
        for node in new_nodes:
            add_reachable(node, res)


def translate_xor(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place) -> OperatorPOWL:
    """
    Translate an XOR split and join in the Petri net into a POWL OperatorPOWL with Operator.XOR.

    Parameters:
    - net: PetriNet (original net)
    - start_place: Place (start of the XOR split)
    - end_place: Place (final end place of the net)

    Returns:
    - OperatorPOWL object representing the XOR operator with translated subnets.

    Raises:
    - Exception if the XOR join is not found or subnets are not disjoint.
    """
    # Step 1: Get outgoing transitions from start_place (XOR split)
    outgoing_transitions = [
        arc.target for arc in net.arcs
        if arc.source == start_place and isinstance(arc.target, PetriNet.Transition)
    ]

    # Step 2: Get incoming transitions to end_place (XOR join)
    incoming_transitions = [
        arc.source for arc in net.arcs
        if arc.target == end_place and isinstance(arc.source, PetriNet.Transition)
    ]

    if len(outgoing_transitions) != len(incoming_transitions):
        raise Exception("Number of outgoing transitions does not match incoming transitions.")

    # Step 3: Iterate over each outgoing transition and collect all nodes in the subnet
    subnets = []
    print(outgoing_transitions)
    for start_transition in reversed(outgoing_transitions):
        # Collect all nodes in this subnet by traversing from out_trans to the XOR join
        subnet_nodes = set()
        subnet_nodes.add(start_transition)
        add_reachable(start_transition, subnet_nodes)
        print(f"from {start_transition} reachable: {subnet_nodes}")
        subnet_nodes.remove(end_place)

        # Validate that subnet contains exactly one end transition (leading to XOR join)
        end_transitions = [t for t in subnet_nodes if
                           isinstance(t, PetriNet.Transition) and end_place in pn_util.post_set(t)]
        if len(end_transitions) != 1:
            raise Exception(
                f"Subnet starting with transition {start_transition.name} does not have exactly one end transition: {end_transitions}")

        end_transition = end_transitions[0]

        subnet_net = PetriNet(f"Subnet_{next(id_gen)}")

        # Introduce fresh start place and fresh end place
        fresh_start_p = PetriNet.Place(f"fresh_start_{next(id_gen)}")
        subnet_net.places.add(fresh_start_p)
        subnet_initial_marking = Marking()
        subnet_initial_marking[fresh_start_p] = 1

        fresh_end_p = PetriNet.Place(f"fresh_end_{next(id_gen)}")
        subnet_net.places.add(fresh_end_p)
        subnet_final_marking = Marking()
        subnet_final_marking[fresh_end_p] = 1

        place_map = {}
        trans_map = {}
        for node in subnet_nodes:
            if isinstance(node, PetriNet.Place):
                cloned_place = PetriNet.Place(f"{node.name}_cloned")
                subnet_net.places.add(cloned_place)
                place_map[node] = cloned_place
            elif isinstance(node, PetriNet.Transition):
                cloned_trans = PetriNet.Transition(f"{node.name}_cloned", node.label)
                subnet_net.transitions.add(cloned_trans)
                trans_map[node] = cloned_trans

        # Add arcs within the subnet
        for arc in net.arcs:
            if arc.source in subnet_nodes and arc.target in subnet_nodes:
                cloned_source = trans_map.get(arc.source, place_map.get(arc.source, None))
                cloned_target = trans_map.get(arc.target, place_map.get(arc.target, None))
                if cloned_source and cloned_target:
                    add_arc_from_to(cloned_source, cloned_target, subnet_net)

        add_arc_from_to(fresh_start_p, trans_map.get(start_transition), subnet_net)
        add_arc_from_to(trans_map.get(end_transition), fresh_end_p, subnet_net)

        subnets.append({
            'net': subnet_net,
            'initial_marking': subnet_initial_marking,
            'final_marking': subnet_final_marking
        })

    # Step 4: Ensure all subnets are disjoint
    check_disjoint_subnets(subnets)

    # Step 5: Recursively translate each subnet into POWL models
    children = []
    for subnet in subnets:
        child_powl = translate_petri_to_powl(
            subnet['net'],
            subnet['initial_marking'],
            subnet['final_marking']
        )
        children.append(child_powl)

    # Step 6: Create and return the XOR OperatorPOWL
    xor_operator = OperatorPOWL(operator=Operator.XOR, children=children)

    return xor_operator


def is_loop(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place) -> bool:
    """
    Determine if the Petri net represents a loop structure.

    A loop is characterized by the start and end places having both incoming and outgoing arcs.
    """
    # Start and end places must have both incoming and outgoing arcs
    start_has_incoming = len(start_place.in_arcs) > 0
    start_has_outgoing = len(start_place.out_arcs) > 0
    end_has_incoming = len(end_place.in_arcs) > 0
    end_has_outgoing = len(end_place.out_arcs) > 0

    print(start_has_incoming)
    print(start_has_outgoing)
    print(end_has_incoming)
    print(end_has_outgoing)

    return (start_has_incoming and start_has_outgoing and
            end_has_incoming and end_has_outgoing and start_place != end_place)


def translate_loop(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place) -> OperatorPOWL:
    """
    Translate a loop structure in the Petri net into a POWL OperatorPOWL with Operator.LOOP.
    """
    # Collect 'do' part nodes (from start_place to end_place)
    do_subnet_nodes = collect_subnet_nodes(net, start_place, end_place)
    do_subnet_nodes.remove(start_place)
    do_subnet_nodes.remove(end_place)

    # Collect 'redo' part nodes (from end_place back to start_place)
    redo_subnet_nodes = collect_subnet_nodes(net, end_place, start_place)
    redo_subnet_nodes.remove(start_place)
    redo_subnet_nodes.remove(end_place)

    # Create subnets for 'do' and 'redo'
    do_subnet = create_subnet(net, do_subnet_nodes, start_place, end_place)
    redo_subnet = create_subnet(net, redo_subnet_nodes, end_place, start_place)

    # Recursively translate the 'do' and 'redo' subnets
    do_powl = translate_petri_to_powl(do_subnet['net'], do_subnet['initial_marking'], do_subnet['final_marking'])
    redo_powl = translate_petri_to_powl(redo_subnet['net'], redo_subnet['initial_marking'],
                                        redo_subnet['final_marking'])

    # Create and return the LOOP OperatorPOWL
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

    place_map = {}
    trans_map = {}
    for node in subnet_nodes:
        if isinstance(node, PetriNet.Place):
            cloned_place = PetriNet.Place(f"{node.name}_cloned")
            subnet_net.places.add(cloned_place)
            place_map[node] = cloned_place
        elif isinstance(node, PetriNet.Transition):
            cloned_trans = PetriNet.Transition(f"{node.name}_cloned", node.label)
            subnet_net.transitions.add(cloned_trans)
            trans_map[node] = cloned_trans

    # Add arcs within the subnet
    for arc in net.arcs:
        if arc.source in subnet_nodes and arc.target in subnet_nodes:
            cloned_source = trans_map.get(arc.source, place_map.get(arc.source))
            cloned_target = trans_map.get(arc.target, place_map.get(arc.target))
            if cloned_source and cloned_target:
                add_arc_from_to(cloned_source, cloned_target, subnet_net)

    # Connect fresh start and end places
    for t in pn_util.post_set(start_place).intersection(subnet_nodes):
        add_arc_from_to(fresh_start_p, trans_map[t], subnet_net)
    for t in pn_util.pre_set(end_place).intersection(subnet_nodes):
        add_arc_from_to(trans_map[t], fresh_end_p, subnet_net)

    return {
        'net': subnet_net,
        'initial_marking': subnet_initial_marking,
        'final_marking': subnet_final_marking
    }


def check_disjoint_subnets(subnets: List[Dict]):
    """
    Ensure that all subnets are disjoint (no shared transitions or places).

    Parameters:
    - subnets: List of subnet dictionaries containing 'net', 'initial_marking', 'final_marking'

    Raises:
    - Exception if any subnets share transitions or places
    """
    all_transitions: Set[PetriNet.Transition] = set()
    all_places: Set[PetriNet.Place] = set()

    for subnet in subnets:
        net_sub = subnet['net']
        # Check for overlapping transitions
        shared_trans = all_transitions.intersection(net_sub.transitions)
        if shared_trans:
            shared_trans_names = [t.name for t in shared_trans]
            raise Exception(f"Subnets share transitions: {shared_trans_names}")
        all_transitions.update(net_sub.transitions)

        # Check for overlapping places
        shared_places = all_places.intersection(net_sub.places)
        if shared_places:
            shared_place_names = [p.name for p in shared_places]
            raise Exception(f"Subnets share places: {shared_place_names}")
        all_places.update(net_sub.places)


def create_simple_petri_net() -> (PetriNet, Marking, Marking):
    """
    Create a simple Petri net with one transition (base case).

    Returns:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking
    """
    net = PetriNet("Simple Net")
    start = PetriNet.Place("start")
    end = PetriNet.Place("end")
    net.places.add(start)
    net.places.add(end)

    t1 = PetriNet.Transition("t1", "Do something")
    net.transitions.add(t1)

    add_arc_from_to(start, t1, net)
    add_arc_from_to(t1, end, net)

    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[start] = 1
    final_marking[end] = 1

    return net, initial_marking, final_marking


def create_petri_net_with_choice(n: int) -> (PetriNet, Marking, Marking):
    """
    Create a Petri net with an XOR split into n base case subnets.

    Parameters:
    - n: Number of choices

    Returns:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking
    """
    net = PetriNet("Enhanced Choice Net with Silent Transitions")

    # Define places
    start = PetriNet.Place("start")
    end = PetriNet.Place("end")
    net.places.add(start)
    net.places.add(end)

    # Create main transition from start to main choice places
    t_main = PetriNet.Transition("t_main", None)
    net.transitions.add(t_main)
    add_arc_from_to(start, t_main, net)

    # Create n main choice places (p1 to pn)
    main_choice_place = PetriNet.Place("p")
    net.places.add(main_choice_place)
    add_arc_from_to(t_main, main_choice_place, net)

    # For the first two main choices, add secondary choices using silent transitions
    for i in range(1, 3):  # Assuming you want to add secondary choices to the first two places
        parent_place = main_choice_place

        # Create a silent transition for splitting
        s = PetriNet.Transition(f"s{i}", None)
        net.transitions.add(s)
        add_arc_from_to(parent_place, s, net)

        # Create an intermediate place between silent transition and sub-transitions
        intermediate_p = PetriNet.Place(f"intermediate_p{i}")
        net.places.add(intermediate_p)
        add_arc_from_to(s, intermediate_p, net)

        intermediate_p2 = PetriNet.Place(f"intermediate2_p{i}")
        net.places.add(intermediate_p2)

        # Create sub-choice transitions (t1_1 to t1_n and t2_1 to t2_n)
        for j in range(1, n + 1):
            sub_t = PetriNet.Transition(f"t{i}_{j}", f"Action {i}_{j}")
            net.transitions.add(sub_t)
            add_arc_from_to(intermediate_p, sub_t, net)
            add_arc_from_to(sub_t, intermediate_p2, net)
        sub_t = PetriNet.Transition(f"t{i}_silent", None)
        net.transitions.add(sub_t)
        add_arc_from_to(intermediate_p, sub_t, net)
        add_arc_from_to(sub_t, intermediate_p2, net)

        sub_t2 = PetriNet.Transition(f"final", None)
        net.transitions.add(sub_t2)

        add_arc_from_to(intermediate_p2, sub_t2, net)
        add_arc_from_to(sub_t2, end, net)

    # For the remaining main choice places, connect directly to end via their transitions
    for i in range(3, n + 1):
        parent_place = main_choice_place
        t = PetriNet.Transition(f"t{i}", f"Action {i}")
        net.transitions.add(t)
        add_arc_from_to(parent_place, t, net)
        add_arc_from_to(t, end, net)

    parent_place = main_choice_place
    t = PetriNet.Transition(f"SILENT", None)
    net.transitions.add(t)
    add_arc_from_to(parent_place, t, net)
    add_arc_from_to(t, end, net)

    second_endt = PetriNet.Transition(f"second_end_t", None)
    net.transitions.add(second_endt)

    second_endp = PetriNet.Place(f"second_end_p")
    net.places.add(second_endp)

    add_arc_from_to(end, second_endt, net)
    add_arc_from_to(second_endt, second_endp, net)

    # Define initial and final markings
    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[start] = 1
    final_marking[second_endp] = 1

    # Visualize the Petri net
    pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")

    powl_model = translate_petri_to_powl(net, initial_marking, final_marking)

    # Visualize the POWL model
    pm4py.view_powl(powl_model, format="SVG")


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


# Testing the conversion
def test_base_case():
    print("=== Testing Base Case ===")
    net, initial_marking, final_marking = create_simple_petri_net()
    powl_model = translate_petri_to_powl(net, initial_marking, final_marking)

    # Visualize the Petri net
    pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")

    # Visualize the POWL model
    pm4py.view_powl(powl_model, format="SVG")

    if isinstance(powl_model, Transition):
        print(f"Converted POWL model: {powl_model.label}")
    else:
        print("Converted POWL model is not a Transition as expected.")


def test_loop(n=5):
    net = PetriNet("Enhanced Choice Net with Silent Transitions")

    # Define places
    start = PetriNet.Place("start")
    end = PetriNet.Place("end")
    net.places.add(start)
    net.places.add(end)

    # Create main transition from start to main choice places
    t_main = PetriNet.Transition("t_main", None)
    net.transitions.add(t_main)
    add_arc_from_to(start, t_main, net)

    # Create n main choice places (p1 to pn)
    main_choice_place = PetriNet.Place("p")
    net.places.add(main_choice_place)
    add_arc_from_to(t_main, main_choice_place, net)

    # For the first two main choices, add secondary choices using silent transitions
    for i in range(1, 3):  # Assuming you want to add secondary choices to the first two places
        parent_place = main_choice_place

        # Create a silent transition for splitting
        s = PetriNet.Transition(f"s{i}", None)
        net.transitions.add(s)
        add_arc_from_to(parent_place, s, net)

        # Create an intermediate place between silent transition and sub-transitions
        intermediate_p = PetriNet.Place(f"intermediate_p{i}")
        net.places.add(intermediate_p)
        add_arc_from_to(s, intermediate_p, net)

        intermediate_p2 = PetriNet.Place(f"intermediate2_p{i}")
        net.places.add(intermediate_p2)

        # Create sub-choice transitions (t1_1 to t1_n and t2_1 to t2_n)
        for j in range(1, n + 1):
            sub_t = PetriNet.Transition(f"t{i}_{j}", f"Action {i}_{j}")
            net.transitions.add(sub_t)
            add_arc_from_to(intermediate_p, sub_t, net)
            add_arc_from_to(sub_t, intermediate_p2, net)
        sub_t = PetriNet.Transition(f"t{i}_silent", None)
        net.transitions.add(sub_t)
        add_arc_from_to(intermediate_p, sub_t, net)
        add_arc_from_to(sub_t, intermediate_p2, net)

        sub_t2 = PetriNet.Transition(f"final", None)
        net.transitions.add(sub_t2)

        add_arc_from_to(intermediate_p2, sub_t2, net)
        add_arc_from_to(sub_t2, end, net)

    # For the remaining main choice places, connect directly to end via their transitions
    for i in range(3, n + 1):
        parent_place = main_choice_place
        t = PetriNet.Transition(f"t{i}", f"Action {i}")
        net.transitions.add(t)
        add_arc_from_to(t, parent_place, net)
        add_arc_from_to(end, t, net)

    parent_place = main_choice_place
    t = PetriNet.Transition(f"SILENT", None)
    net.transitions.add(t)
    add_arc_from_to(parent_place, t, net)
    add_arc_from_to(t, end, net)

    second_endt = PetriNet.Transition(f"second_end_t", None)
    net.transitions.add(second_endt)

    second_endp = PetriNet.Place(f"second_end_p")
    net.places.add(second_endp)

    add_arc_from_to(end, second_endt, net)
    add_arc_from_to(second_endt, second_endp, net)

    # Define initial and final markings
    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[start] = 1
    final_marking[second_endp] = 1

    # Visualize the Petri net
    pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")

    powl_model = translate_petri_to_powl(net, initial_marking, final_marking)

    # Visualize the POWL model
    pm4py.view_powl(powl_model, format="SVG")


def test_simple_loop(n=5):
    net = PetriNet("Minimal Loop Workflow Net")

    # Define places
    p_start = PetriNet.Place("p_start")
    p1 = PetriNet.Place("p1")
    p11 = PetriNet.Place("p11")
    p_end = PetriNet.Place("p_end")
    net.places.update([p_start, p1, p11, p_end])

    # Define transitions
    t1 = PetriNet.Transition("t1", None)
    t2 = PetriNet.Transition("t2", "Action 2")  # Loop transition
    t22 = PetriNet.Transition("t22", "Action 3")
    t3 = PetriNet.Transition("t3", None)
    net.transitions.update([t1, t2, t22, t3])

    # Add arcs
    add_arc_from_to(p_start, t1, net)
    add_arc_from_to(t1, p1, net)
    add_arc_from_to(p1, t2, net)
    add_arc_from_to(t2, p11, net)
    add_arc_from_to(p11, t22, net)
    add_arc_from_to(t22, p1, net)
    # Loop back to p1
    add_arc_from_to(p11, t3, net)
    add_arc_from_to(t3, p_end, net)

    # Define initial and final markings
    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[p_start] = 1
    final_marking[p_end] = 1

    # Visualize the Petri net
    pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")

    powl_model = translate_petri_to_powl(net, initial_marking, final_marking)

    # Visualize the POWL model
    pm4py.view_powl(powl_model, format="SVG")


if __name__ == "__main__":
    # Run tests
    # test_base_case()
    # create_petri_net_with_choice(5)
    test_loop()
    # test_simple_loop()
