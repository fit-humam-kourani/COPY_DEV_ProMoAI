from collections import deque
from typing import Union, Dict, Set

from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util
from pm4py.objects.powl.obj import Transition, SilentTransition


def id_generator():
    count = 1
    while True:
        yield f"id{count}"
        count += 1


def collect_subnet_transitions(source_place: PetriNet.Place, target_place: PetriNet.Place) -> Set[PetriNet.Transition]:
    """
    Collect all transitions in the subnet from source_place to target_place.
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
    # visited.remove(source_place)
    # visited.remove(target_place)
    visited = {node for node in visited if isinstance(node, PetriNet.Transition)}
    return visited


def clone_place(net, place, node_map):
    cloned_place = PetriNet.Place(f"{place.name}_cloned")
    net.places.add(cloned_place)
    node_map[place] = cloned_place
    return cloned_place


def clone_transition(net, transition, node_map):
    cloned_transition = PetriNet.Transition(f"{transition.name}_cloned", transition.label)
    net.transitions.add(cloned_transition)
    node_map[transition] = cloned_transition
    return cloned_transition


def check_and_repair_markings(net, subnet_net, node_map, start_places, end_places):
    if len(start_places) == 0 or len(end_places) == 0:
        print(net, start_places, end_places)
        raise Exception("This should not happen!")
    start_place = start_places[0]
    if len(start_places) > 1:
        for p in start_places[1:]:
            if pn_util.post_set(node_map[p]) != pn_util.post_set(node_map[start_place]):
                raise Exception("This should not happen!")
            subnet_net = pn_util.remove_place(subnet_net, node_map[p])
    end_place = end_places[0]
    if len(end_places) > 1:
        for p in end_places[1:]:
            if pn_util.pre_set(node_map[p]) != pn_util.pre_set(node_map[end_place]):
                raise Exception("This should not happen!")
            subnet_net = pn_util.remove_place(subnet_net, node_map[p])

    if len(node_map[start_place].in_arcs) > 0:
        new_id = next(id_generator())
        new_start = PetriNet.Place(name=f"new_start_{new_id}")
        silent_start = PetriNet.Transition(name=f"silent_start{new_id}", label=None)
        subnet_net.places.add(new_start)
        subnet_net.transitions.add(silent_start)
        add_arc_from_to(new_start, silent_start, subnet_net)
        add_arc_from_to(silent_start, node_map[start_place], subnet_net)
    else:
        new_start = node_map[start_place]

    if len(node_map[end_place].out_arcs) > 0:
        new_id = next(id_generator())
        new_end = PetriNet.Place(name=f"new_end_{new_id}")
        silent_end = PetriNet.Transition(name=f"silent_end{new_id}", label=None)
        subnet_net.places.add(new_end)
        subnet_net.transitions.add(silent_end)
        add_arc_from_to(node_map[end_place], silent_end, subnet_net)
        add_arc_from_to(silent_end, new_end, subnet_net)
    else:
        new_end = node_map[end_place]

    return subnet_net, new_start, new_end



def create_subnet(net: PetriNet, subnet_transitions: Set[PetriNet.Transition], start_place, end_place) -> Dict:
    """
    Create a subnet Petri net from the given nodes.
    """
    subnet_net = PetriNet(f"Subnet_{next(id_generator())}")
    node_map = {}

    for node in subnet_transitions:
        clone_transition(subnet_net, node, node_map)

    # Add arcs and remaining places of the subnet
    for arc in net.arcs:
        source = arc.source
        target = arc.target
        if source in subnet_transitions or target in subnet_transitions:
            if source in node_map.keys():
                cloned_source = node_map[source]
            else:
                cloned_source = clone_place(subnet_net, source, node_map)
            if target in node_map.keys():
                cloned_target = node_map[target]
            else:
                cloned_target = clone_place(subnet_net, target, node_map)
            add_arc_from_to(cloned_source, cloned_target, subnet_net)

    subnet_net, new_start, new_end = check_and_repair_markings(net, subnet_net, node_map, start_place, end_place)

    subnet_initial_marking = Marking()
    subnet_initial_marking[new_start] = 1

    subnet_final_marking = Marking()
    subnet_final_marking[new_end] = 1


    return {
        'net': subnet_net,
        'initial_marking': subnet_initial_marking,
        'final_marking': subnet_final_marking
    }


# def create_subnet_over_nodes(net: PetriNet, subnet_nodes: Set[Union[PetriNet.Place, PetriNet.Transition]],
#                              old_start_place, old_end_place):
#     """
#     Create a subnet Petri net from the given nodes.
#     """
#
#     subnet_net = PetriNet(f"Subnet_{next(id_gen)}")
#
#     node_map = {}
#     for node in subnet_nodes:
#         if isinstance(node, PetriNet.Place):
#             cloned_place = PetriNet.Place(f"{node.name}_cloned")
#             subnet_net.places.add(cloned_place)
#             node_map[node] = cloned_place
#         elif isinstance(node, PetriNet.Transition):
#             cloned_trans = PetriNet.Transition(f"{node.name}_cloned", node.label)
#             subnet_net.transitions.add(cloned_trans)
#             node_map[node] = cloned_trans
#
#     # Add arcs within the subnet
#     for arc in net.arcs:
#         if arc.source in subnet_nodes and arc.target in subnet_nodes:
#             cloned_source = node_map[arc.source]
#             cloned_target = node_map[arc.target]
#             add_arc_from_to(cloned_source, cloned_target, subnet_net)
#
#     init_p = PetriNet.Place(f"fresh_start_{next(id_gen)}")
#     subnet_net.places.add(init_p)
#     final_p = PetriNet.Place(f"fresh_end_{next(id_gen)}")
#     subnet_net.places.add(final_p)
#
#     if old_start_place in subnet_nodes:
#         init_places = [old_start_place]
#     else:
#         init_places = [node for node in subnet_nodes if
#                        isinstance(node, PetriNet.Place) and len(node_map[node].in_arcs) < len(node.in_arcs)]
#     if old_end_place in subnet_nodes:
#         final_places = [old_end_place]
#     else:
#         final_places = [node for node in subnet_nodes if
#                         isinstance(node, PetriNet.Place) and len(node_map[node].out_arcs) < len(node.out_arcs)]
#
#     if len(init_places) == len(final_places) == 1:
#         second_p = node_map[init_places[0]]
#         second_last_p = node_map[final_places[0]]
#         t_silent = PetriNet.Transition(f"silent{id_generator()}", None)
#         subnet_net.transitions.add(t_silent)
#         add_arc_from_to(init_p, t_silent, subnet_net)
#         add_arc_from_to(t_silent, second_p, subnet_net)
#         t_silent2 = PetriNet.Transition(f"silent{id_generator()}", None)
#         subnet_net.transitions.add(t_silent2)
#         add_arc_from_to(second_last_p, t_silent2, subnet_net)
#         add_arc_from_to(t_silent2, final_p, subnet_net)
#
#     elif len(init_places) == len(final_places) == 0:
#         init_transitions = [node for node in subnet_nodes if
#                             isinstance(node, PetriNet.Transition) and len(node_map[node].in_arcs) < len(node.in_arcs)]
#         final_transitions = [node for node in subnet_nodes if
#                              isinstance(node, PetriNet.Transition) and len(node_map[node].out_arcs) < len(
#                                  node.out_arcs)]
#
#         if len(init_transitions) == 0 or len(final_transitions) == 0:
#             raise Exception("This should not happen!")
#
#         for t in init_transitions:
#             add_arc_from_to(init_p, node_map[t], subnet_net)
#         for t in final_transitions:
#             add_arc_from_to(node_map[t], final_p, subnet_net)
#     else:
#         raise Exception("This should not happen!")
#
#     subnet_initial_marking = Marking()
#     subnet_initial_marking[init_p] = 1
#     subnet_final_marking = Marking()
#     subnet_final_marking[final_p] = 1
#     return {
#         'net': subnet_net,
#         'initial_marking': subnet_initial_marking,
#         'final_marking': subnet_final_marking
#     }


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


def pn_transition_to_powl(transition: PetriNet.Transition) -> Transition:
    label = transition.label
    if label:
        return Transition(label=label)
    else:
        return SilentTransition()
