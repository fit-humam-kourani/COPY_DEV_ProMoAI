import pm4py
from pm4py.objects.powl.obj import POWL, Transition, OperatorPOWL, Operator, StrictPartialOrder, SilentTransition, \
    Sequence

from utils.pn_to_powl.tests import test_po
from utils.pn_to_powl.utils.cut_detection import *
from utils.pn_to_powl.utils.preprocessing import *
from utils.pn_to_powl.utils.reachability_map import *
from utils.pn_to_powl.utils.subnet_creation import *


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
    start_place, end_place = validate_petri_net(net, initial_marking, final_marking)

    start_place, end_place = preprocess_net(net, start_place, end_place)

    # Check for base case
    transition = mine_base_case(net, start_place, end_place)
    if transition:
        print("Base case detected")
        return __translate_single_transition(transition)

    reachability_map = get_reachable_nodes_mapping(net)
    full_reachability_map = get_reachability_graph(net)

    # Check for Sequence split
    seq_points, sorted_places = mine_sequence(net, start_place, end_place, full_reachability_map)
    # we need at least three connection poits for a sequence: start_place, cut_point, end_place
    if len(seq_points) > 2:
        print("Seq detected")
        return __translate_seq(net, seq_points, sorted_places, reachability_map)

    # Check for XOR split
    choice_branches = mine_xor(net, start_place, end_place)
    if choice_branches and len(choice_branches) > 1:
        print("XOR detected")
        return __translate_xor(net, start_place, end_place, choice_branches)

    do, redo = mine_loop(net, start_place, end_place)
    if do and redo:
        print("Loop detected")
        return __translate_loop(net, do, redo, start_place, end_place)

    full_reachability_map = get_reachability_graph(net)

    partitions = mine_partial_order(net, start_place, end_place, full_reachability_map)
    if partitions:
        return __translate_partial_order(net, partitions, start_place, end_place)

    # raise NotImplementedError("This type of Petri net structure is not yet implemented.")


def __translate_single_transition(transition: PetriNet.Transition) -> Transition:
    label = transition.label
    if label:
        return Transition(label=label)
    else:
        return SilentTransition()


def __translate_xor(net: PetriNet, start_place: PetriNet.Place, end_place: PetriNet.Place, choice_branches):
    children = []
    for branch in choice_branches:
        child_powl = __create_sub_powl_model(net, branch, start_place, end_place)
        children.append(child_powl)
    xor_operator = OperatorPOWL(operator=Operator.XOR, children=children)
    return xor_operator


def __translate_loop(net: PetriNet, do_nodes, redo_nodes, start_place: PetriNet.Place,
                     end_place: PetriNet.Place) -> OperatorPOWL:
    do_powl = __create_sub_powl_model(net, do_nodes, start_place, end_place)
    redo_powl = __create_sub_powl_model(net, redo_nodes, end_place, start_place)
    loop_operator = OperatorPOWL(operator=Operator.LOOP, children=[do_powl, redo_powl])
    return loop_operator


def __translate_partial_order(net, partitions, start_place, end_place):
    groups = [group for group in partitions if len(group) > 1]
    nodes_not_grouped = [group[0] for group in partitions if len(group) == 1]
    transitions_not_grouped = [node for node in nodes_not_grouped if isinstance(node, PetriNet.Transition)]
    # places_not_grouped = [node for node in nodes_not_grouped if isinstance(node, PetriNet.Place)]
    children = []
    node_to_powl_map = {}
    for group in groups:
        # print(group)
        subnet = create_subnet_over_nodes(net, set(group), start_place, end_place)
        child = translate_petri_to_powl(
            subnet['net'],
            subnet['initial_marking'],
            subnet['final_marking']
        )
        for node in group:
            node_to_powl_map[node] = child
        children.append(child)
    for transition in transitions_not_grouped:
        powl = __translate_single_transition(transition)
        children.append(powl)
        node_to_powl_map[transition] = powl
    po = StrictPartialOrder(children)
    for place in net.places:
        sources = set([node_to_powl_map[arc.source] for arc in place.in_arcs])
        targets = set([node_to_powl_map[arc.target] for arc in place.out_arcs])
        for new_source in sources:
            for new_target in targets:
                if new_source != new_target:
                    po.order.add_edge(new_source, new_target)

        # else:
        #     raise Exception("This should not happen!")
    return po


def __translate_seq(net, connection_points, ordered_places, reachability_map):
    powl_sub_models = []
    index = 0
    # excluded last place, which must be a connection point (otherwise, exception would have been thrown earlier)
    for i in range(len(ordered_places) - 1):
        p = ordered_places[i]
        if p in connection_points:
            node_map = {}

            index = index + 1
            sub_net = PetriNet(f"Subnet_{index}")
            sub_start_place = PetriNet.Place(name=f"{p.name}_subnet{index}")
            node_map[p] = sub_start_place
            sub_net.places.add(sub_start_place)
            subnet_initial_marking = Marking()
            subnet_final_marking = Marking()
            subnet_initial_marking[sub_start_place] = 1
            p_next = None
            # add all next places until reaching a connection point
            for j in range(i + 1, len(ordered_places)):
                p_next = ordered_places[j]
                cloned_place = PetriNet.Place(name=f"{p_next.name}_subnet{index}")
                sub_net.places.add(cloned_place)
                node_map[p_next] = cloned_place
                if p_next in connection_points:
                    subnet_final_marking[cloned_place] = 1
                    break

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


def __create_sub_powl_model(net, branch, start_place, end_place):
    subnet = create_subnet(net, branch, start_place, end_place)
    return translate_petri_to_powl(
        subnet['net'],
        subnet['initial_marking'],
        subnet['final_marking']
    )


if __name__ == "__main__":
    # net, im, fm = test_choice2()
    # net, im, fm = test_loop()
    pn, im, fm = test_po()

    pm4py.view_petri_net(pn, im, fm, format="SVG")
    powl_model = translate_petri_to_powl(pn, im, fm)
    pm4py.view_powl(powl_model, format="SVG")
