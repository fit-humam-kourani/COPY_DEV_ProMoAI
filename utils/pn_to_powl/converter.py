from pm4py.objects.powl.BinaryRelation import BinaryRelation
from pm4py.objects.powl.obj import POWL, OperatorPOWL, Operator, StrictPartialOrder

from utils.pn_to_powl.converter_utils.cut_detection import mine_base_case, mine_xor, mine_loop, mine_partial_order, \
    mine_self_loop
from utils.pn_to_powl.converter_utils.reachability_map import get_reachability_graph, generate_reachability_graph
from utils.pn_to_powl.tests import *

from utils.pn_to_powl.converter_utils.preprocessing import validate_petri_net, preprocess_net, remove_duplicate_places
from utils.pn_to_powl.converter_utils.subnet_creation import create_subnet, \
    pn_transition_to_powl


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
    # print("Transitions: ", net.transitions)
    # print("Places: ", net.places)
    # print("initial_marking: ", initial_marking)
    # print("final_marking: ", final_marking)
    # print("Arcs: ", net.arcs)

    # Validation and preprocessing for base case
    i_place, e_place = validate_petri_net(net, initial_marking, final_marking)
    start_places, end_places = preprocess_net(net, i_place, e_place)
    # print("Transitions: ", net.transitions)
    # print("Places: ", net.places)
    # print("initial_marking: ", start_places)
    # print("final_marking: ", end_places)
    # print("Arcs: ", net.arcs)
    start_places, end_places = remove_duplicate_places(net, start_places, end_places)
    # print("Transitions: ", net.transitions)
    # print("Places: ", net.places)
    # print("initial_marking: ", start_places)
    # print("final_marking: ", end_places)
    # print("Arcs: ", net.arcs)


    # Mine for base case
    base_case = mine_base_case(net)
    if base_case:
        print("Base case detected: ", base_case)
        return base_case

    self_loop = mine_self_loop(net, start_places, end_places)
    if self_loop:
        print("Self_loop detected!")
        return __translate_loop(net, self_loop[0], self_loop[1], self_loop[2], self_loop[3])

    im = Marking()
    for p in start_places:
        im[p] = 1
    fm = Marking()
    for p in end_places:
        fm[p] = 1

    reachab_graph, map_states, transition_map = generate_reachability_graph(net, im)

    # Mine for XOR
    choice_branches = mine_xor(im, map_states, transition_map)
    if choice_branches and len(choice_branches) > 1:
        print("XOR detected: ", choice_branches)
        return __translate_xor(net, start_places, end_places, choice_branches)

    # Mine for Loop
    do, redo = mine_loop(net, im, fm, map_states, transition_map)
    if do and redo:
        print("Loop detected")
        return __translate_loop(net, do, redo, start_places, end_places)

    full_reachability_map = get_reachability_graph(net)
    # Mine for partial order
    partitions = mine_partial_order(net, start_places, end_places, full_reachability_map)
    if len(partitions) > 1:
        print(f"PO detected: {partitions}")
        return __translate_partial_order(net, partitions, start_places, end_places)

    pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")
    raise Exception(f"Failed to detected a POWL structure over the following transitions: {net.transitions}")


def __translate_xor(net: PetriNet, start_places: set[PetriNet.Place], end_places: set[PetriNet.Place], choice_branches):
    children = []
    for branch in choice_branches:
        child_powl = __create_sub_powl_model(net, branch, start_places, end_places)
        children.append(child_powl)
    xor_operator = OperatorPOWL(operator=Operator.XOR, children=children)
    return xor_operator


def __translate_loop(net: PetriNet, do_nodes, redo_nodes, start_places, end_places) -> OperatorPOWL:
    print("LOOP")
    print(net)
    do_powl = __create_sub_powl_model(net, do_nodes, start_places, end_places)
    redo_powl = __create_sub_powl_model(net, redo_nodes, end_places, start_places)
    loop_operator = OperatorPOWL(operator=Operator.LOOP, children=[do_powl, redo_powl])
    return loop_operator


def __translate_partial_order(net, transition_groups, i_places: set[PetriNet.Place], f_places: set[PetriNet.Place]):

    groups_as_tuples = [tuple(g) for g in transition_groups]
    start_places = {g: set() for g in groups_as_tuples}
    end_places = {g: set() for g in groups_as_tuples}
    transition_to_group = {}
    for g in groups_as_tuples:
        for member in g:
            transition_to_group[member] = g

    temp_po = BinaryRelation(groups_as_tuples)
    for place in net.places:
        sources = set([arc.source for arc in place.in_arcs])
        targets = set([arc.target for arc in place.out_arcs])
        if place in i_places:
            for target in targets:
                group_target = transition_to_group[target]
                start_places[group_target].add(place)
        if place in f_places:
            for source in sources:
                group_source = transition_to_group[source]
                end_places[group_source].add(place)

        for source in sources:
            group_source = transition_to_group[source]
            for target in targets:
                group_target = transition_to_group[target]
                if group_source != group_target:
                    temp_po.add_edge(group_source, group_target)
                    end_places[group_source].add(place)
                    start_places[group_target].add(place)

    group_to_powl_map = {}
    children = []
    print("TUPLES:", groups_as_tuples)
    for group in groups_as_tuples:
        init_p = list(start_places[group])
        final_p = list(end_places[group])
        child = __create_sub_powl_model(net, set(group), init_p, final_p)
        group_to_powl_map[group] = child
        children.append(child)

    po = StrictPartialOrder(children)
    for source in temp_po.nodes:
        new_source = group_to_powl_map[source]
        for target in temp_po.nodes:
            if temp_po.is_edge(source, target):
                new_target = group_to_powl_map[target]
                po.order.add_edge(new_source, new_target)
    return po


# def __translate_seq(net, connection_points, ordered_places, reachability_map):
#     powl_sub_models = []
#     index = 0
#     # excluded last place, which must be a connection point (otherwise, exception would have been thrown earlier)
#     for i in range(len(ordered_places) - 1):
#         p = ordered_places[i]
#         if p in connection_points:
#             node_map = {}
#
#             index = index + 1
#             sub_net = PetriNet(f"Subnet_{index}")
#             sub_start_place = PetriNet.Place(name=f"{p.name}_subnet{index}")
#             node_map[p] = sub_start_place
#             sub_net.places.add(sub_start_place)
#             subnet_initial_marking = Marking()
#             subnet_final_marking = Marking()
#             subnet_initial_marking[sub_start_place] = 1
#             p_next = None
#             # add all next places until reaching a connection point
#             for j in range(i + 1, len(ordered_places)):
#                 p_next = ordered_places[j]
#                 cloned_place = PetriNet.Place(name=f"{p_next.name}_subnet{index}")
#                 sub_net.places.add(cloned_place)
#                 node_map[p_next] = cloned_place
#                 if p_next in connection_points:
#                     subnet_final_marking[cloned_place] = 1
#                     break
#
#             # add transitions
#             for t in net.transitions:
#                 if t in reachability_map[p] and t not in reachability_map[p_next]:
#                     new_t = PetriNet.Transition(f"{t.name}_subnet{index}", t.label)
#                     sub_net.transitions.add(new_t)
#                     node_map[t] = new_t
#
#             # add arcs
#             for arc in net.arcs:
#                 source = arc.source
#                 target = arc.target
#                 if source in node_map.keys() and target in node_map.keys():
#                     add_arc_from_to(node_map[source], node_map[target], sub_net)
#
#             powl = translate_petri_to_powl(sub_net, subnet_initial_marking, subnet_final_marking)
#             powl_sub_models.append(powl)
#
#     return Sequence(nodes=powl_sub_models)


def __create_sub_powl_model(net, branch, start_places, end_places):
    subnet = create_subnet(net, branch, start_places, end_places)
    return translate_petri_to_powl(
        subnet['net'],
        subnet['initial_marking'],
        subnet['final_marking']
    )


if __name__ == "__main__":
    # pn, im, fm = test_choice()
    pn, im, fm = test_loop()
    # pn, im, fm = test_po()
    # pn, im, fm = test_xor_ending_and_starting_with_par()

    pm4py.view_petri_net(pn, im, fm, format="SVG")
    powl_model = translate_petri_to_powl(pn, im, fm)
    print(powl_model)

    pm4py.view_powl(powl_model, format="SVG")
