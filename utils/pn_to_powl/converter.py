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

SIMPLIFIED_REACHABILITY = True


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
    res = __translate_petri_to_powl(net, {start_place}, {end_place})
    return res


def __translate_petri_to_powl(net: PetriNet, start_places: set[PetriNet.Place],
                              end_places: set[PetriNet.Place]) -> POWL:
    start_places, end_places = remove_initial_and_end_silent_activities(net, start_places, end_places)
    start_places, end_places = remove_unconnected_places(net, start_places, end_places)
    start_places, end_places = remove_duplicated_places(net, start_places, end_places)
    start_places, end_places = add_new_start_and_end_if_needed(net, start_places, end_places)
    # pm4py.view_petri_net(net, None, None, format="SVG")
    # print(start_places, end_places)

    base_case = mine_base_case(net)
    if base_case:
        return base_case

    self_loop = mine_self_loop(net, start_places, end_places)
    if self_loop:
        return __translate_loop(net, self_loop[0], self_loop[1], self_loop[2], self_loop[3])

    if SIMPLIFIED_REACHABILITY:
        im = fm = map_states = transition_map = None
        reachability_map = get_simplified_reachability_graph(net)
    else:
        im = Marking()
        for p in start_places:
            im[p] = 1
        fm = Marking()
        for p in end_places:
            fm[p] = 1
        reachability_map, map_states, transition_map = generate_reachability_graph(net, im)

    if len(start_places) == 1 == len(end_places):
        # for xor and loops we should have a unique start/end place due to the performed preprocessing step
        start_place = list(start_places)[0]
        end_place = list(end_places)[0]

        choice_branches = mine_xor(net, start_place, reachability_map, transition_map, SIMPLIFIED_REACHABILITY)
        if len(choice_branches) > 1:
            return __translate_xor(net, start_places, end_places, choice_branches)

        do, redo = mine_loop(net, start_place, end_place, im, fm, map_states, transition_map, SIMPLIFIED_REACHABILITY)
        if do and redo:
            return __translate_loop(net, do, redo, start_places, end_places)

    partitions = mine_partial_order(net, reachability_map, transition_map, SIMPLIFIED_REACHABILITY)
    if len(partitions) > 1:
        return __translate_partial_order(net, partitions, start_places, end_places)

    # pm4py.view_petri_net(net, im, fm, format="SVG")
    raise Exception(f"Failed to detected a POWL structure over the following transitions: {net.transitions}")


def __translate_xor(net: PetriNet, start_places: set[PetriNet.Place], end_places: set[PetriNet.Place],
                    choice_branches: list[set[PetriNet.Transition]]):
    children = []
    for branch in choice_branches:
        child_powl = __create_sub_powl_model(net, branch, start_places, end_places)
        children.append(child_powl)
    xor_operator = OperatorPOWL(operator=Operator.XOR, children=children)
    return xor_operator


def __translate_loop(net: PetriNet, do_nodes, redo_nodes,
                     start_places: set[PetriNet.Place],
                     end_places: set[PetriNet.Place]) -> OperatorPOWL:
    do_powl = __create_sub_powl_model(net, do_nodes, start_places, end_places)
    redo_powl = __create_sub_powl_model(net, redo_nodes, end_places, start_places)
    loop_operator = OperatorPOWL(operator=Operator.LOOP, children=[do_powl, redo_powl])
    return loop_operator


def __validate_partial_order(po: StrictPartialOrder):
    po.order.add_transitive_edges()
    if po.order.is_irreflexive():
        return po
    else:
        raise Exception("Conversion failed!")


def __translate_partial_order(net, transition_groups, i_places: set[PetriNet.Place], f_places: set[PetriNet.Place]):

    groups = [tuple(g) for g in transition_groups]
    transition_to_group_map = {transition: g for g in groups for transition in g}

    group_start_places = {g: set() for g in groups}
    group_end_places = {g: set() for g in groups}
    temp_po = BinaryRelation(groups)

    for p in net.places:
        sources = {arc.source for arc in p.in_arcs}
        targets = {arc.target for arc in p.out_arcs}

        # if p is start place and (p -> t), then p should be a start place in the subnet that contains t
        if p in i_places:
            for t in targets:
                group_start_places[transition_to_group_map[t]].add(p)
        # if p is end place and (t -> p), then p should be end place in the subnet that contains t
        if p in f_places:
            for t in sources:
                group_end_places[transition_to_group_map[t]].add(p)

        # if (t1 -> p -> t2) and t1 and t2 are in different subsets, then add an edge in the partial order
        # and set p as end place in g1 and as start place in g2
        for t1 in sources:
            group_1 = transition_to_group_map[t1]
            for t2 in targets:
                group_2 = transition_to_group_map[t2]
                if group_1 != group_2:
                    temp_po.add_edge(group_1, group_2)
                    group_end_places[group_1].add(p)
                    group_start_places[group_2].add(p)

    group_to_powl_map = {}
    children = []
    for group in groups:
        child = __create_sub_powl_model(net, set(group), group_start_places[group], group_end_places[group])
        group_to_powl_map[group] = child
        children.append(child)

    po = StrictPartialOrder(children)
    for source in temp_po.nodes:
        new_source = group_to_powl_map[source]
        for target in temp_po.nodes:
            if temp_po.is_edge(source, target):
                new_target = group_to_powl_map[target]
                po.order.add_edge(new_source, new_target)

    po = __validate_partial_order(po)
    return po


def __create_sub_powl_model(net, branch: set[PetriNet.Transition],
                            start_places: set[PetriNet.Place],
                            end_places: set[PetriNet.Place]):
    subnet, subnet_start_places, subnet_end_places = clone_subnet(net, branch, start_places, end_places)
    powl = __translate_petri_to_powl(subnet, subnet_start_places, subnet_end_places)
    return powl


if __name__ == "__main__":
    # pn, init_mark, final_mark = test_choice()
    # pn, init_mark, final_mark = test_loop()
    # pn, init_mark, final_mark = test_po()
    pn, init_mark, final_mark = create_ld()
    # pn, init_mark, final_mark = test_loop_ending_with_par2()
    # pn, init_mark, final_mark = test_xor_ending_and_starting_with_par()

    pm4py.view_petri_net(pn, init_mark, final_mark, format="SVG")
    powl_model = convert_workflow_net_to_powl(pn, init_mark, final_mark)

    pm4py.view_powl(powl_model, format="SVG")
