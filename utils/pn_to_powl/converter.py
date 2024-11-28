from pm4py.objects.powl.BinaryRelation import BinaryRelation
from pm4py.objects.powl.obj import OperatorPOWL, POWL, Operator, StrictPartialOrder

from utils.pn_to_powl.converter_utils.cut_detection import mine_base_case, mine_xor, mine_loop, mine_partial_order, \
    mine_self_loop
from utils.pn_to_powl.converter_utils.reachability_graph import generate_reachability_graph
from utils.pn_to_powl.converter_utils.weak_reachability import get_simplified_reachability_graph
from utils.pn_to_powl.tests import *

from utils.pn_to_powl.converter_utils.preprocessing import validate_workflow_net, remove_duplicated_places, \
    remove_unconnected_places, \
    add_new_start_and_end_if_needed, remove_initial_and_end_silent_activities
from utils.pn_to_powl.converter_utils.subnet_creation import clone_subnet

SIMPLIFIED_REACHABILITY = False


def convert_workflow_net_to_powl(net: PetriNet, initial_marking: Marking, final_marking: Marking) -> POWL:
    """
    Convert a Petri net to a POWL model.

    Parameters:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking

    Returns:
    - POWL model
    """
    start_place, end_place = validate_workflow_net(net, initial_marking, final_marking)
    return __translate_petri_to_powl(net, {start_place}, {end_place})


def __translate_petri_to_powl(net: PetriNet, start_places: set[PetriNet.Place],
                              end_places: set[PetriNet.Place]) -> POWL:
    """
    Convert a Petri net to a POWL model.

    Parameters:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking

    Returns:
    - POWL model
    """

    start_places, end_places = remove_initial_and_end_silent_activities(net, start_places, end_places)
    # pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")
    start_places, end_places = remove_unconnected_places(net, start_places, end_places)
    start_places, end_places = remove_duplicated_places(net, start_places, end_places)
    start_places, end_places = add_new_start_and_end_if_needed(net, start_places, end_places)

    im = Marking()
    for p in start_places:
        im[p] = 1
    fm = Marking()
    for p in end_places:
        fm[p] = 1

    base_case = mine_base_case(net)
    if base_case:
        return base_case

    self_loop = mine_self_loop(net, start_places, end_places)
    if self_loop:
        return __translate_loop(net, self_loop[0], self_loop[1], self_loop[2], self_loop[3])

    if SIMPLIFIED_REACHABILITY:
        map_states = transition_map = None
        reachability_map = get_simplified_reachability_graph(net)
    else:
        reachability_map, map_states, transition_map = generate_reachability_graph(net, im)

    choice_branches = mine_xor(net, im, fm, reachability_map, transition_map, SIMPLIFIED_REACHABILITY)
    if len(choice_branches) > 1:
        return __translate_xor(net, start_places, end_places, choice_branches)

    do, redo = mine_loop(net, im, fm, map_states, transition_map, SIMPLIFIED_REACHABILITY)
    if do and redo:
        return __translate_loop(net, do, redo, start_places, end_places)

    partitions = mine_partial_order(net, reachability_map, transition_map, SIMPLIFIED_REACHABILITY)
    if len(partitions) > 1:
        return __translate_partial_order(net, partitions, start_places, end_places)

    # pm4py.view_petri_net(net, im, fm, format="SVG")
    raise Exception(f"Failed to detected a POWL structure over the following transitions: {net.transitions}")


def __translate_xor(net: PetriNet, start_places: set[PetriNet.Place], end_places: set[PetriNet.Place], choice_branches):
    children = []
    for branch in choice_branches:
        child_powl = __create_sub_powl_model(net, branch, start_places, end_places)
        children.append(child_powl)
    xor_operator = OperatorPOWL(operator=Operator.XOR, children=children)
    return xor_operator


def __translate_loop(net: PetriNet, do_nodes, redo_nodes, start_places, end_places) -> OperatorPOWL:
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


def __create_sub_powl_model(net, branch, start_places, end_places):
    subnet, subnet_start_places, subnet_end_places = clone_subnet(net, branch, start_places, end_places)
    powl = translate_petri_to_powl(subnet, subnet_start_places, subnet_end_places)
    return powl


if __name__ == "__main__":
    # pn, init_mark, final_mark = test_choice()
    # pn, init_mark, final_mark = test_loop()
    pn, init_mark, final_mark = test_po()
    # pn, init_mark, final_mark = test_loop_ending_with_par2()
    # pn, init_mark, final_mark = test_xor_ending_and_starting_with_par()

    pm4py.view_petri_net(pn, init_mark, final_mark, format="SVG")
    powl_model = translate_petri_to_powl(pn, init_mark, final_mark)

    pm4py.view_powl(powl_model, format="SVG")
