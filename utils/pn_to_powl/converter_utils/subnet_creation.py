from typing import Union, Set
from pm4py.objects.petri_net.obj import PetriNet
from pm4py.objects.powl.obj import Transition, SilentTransition


def id_generator():
    count = 1
    while True:
        yield f"id{count}"
        count += 1


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


def clone_subnet(net: PetriNet, subnet_transitions: Set[PetriNet.Transition], start_places, end_places):
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

    mapped_start_places = {node_map[p] for p in start_places}
    mapped_end_places = {node_map[p] for p in end_places}

    return subnet_net, mapped_start_places, mapped_end_places


def add_arc_from_to(source: Union[PetriNet.Place, PetriNet.Transition],
                    target: Union[PetriNet.Transition, PetriNet.Place], net: PetriNet):
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
