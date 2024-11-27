from typing import Union, Dict, Set
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util
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


def check_and_repair_markings(subnet_net, node_map, start_places, end_places):
    start_places = list(start_places)
    end_places = list(end_places)

    if len(start_places) == 0 or len(end_places) == 0:
        raise Exception("This should not happen!")

    if len(start_places) > 1:
        shared_pre_set = set(pn_util.pre_set(node_map[start_places[0]]))
        len_pre_set_first = len(shared_pre_set)
        for p in start_places[1:]:
            shared_pre_set &= set(pn_util.pre_set(node_map[p]))
        shared_post_set = set(pn_util.post_set(node_map[start_places[0]]))
        len_post_set_first = len(shared_post_set)
        for p in start_places[1:]:
            shared_post_set &= set(pn_util.post_set(node_map[p]))

        if len_pre_set_first == len(shared_pre_set) and len_post_set_first == len(shared_post_set):
            for p in start_places[1:]:
                pn_util.remove_place(subnet_net, node_map[p])
            start_place = node_map[start_places[0]]
        else:
            new_silent = PetriNet.Transition(f"silent_start_{next(id_generator())}")
            subnet_net.transitions.add(new_silent)

            new_source = PetriNet.Place(f"source_{next(id_generator())}")
            subnet_net.places.add(new_source)

            arcs = list(subnet_net.arcs)
            mapped_start_places = [node_map[p] for p in start_places]
            for arc in arcs:
                source = arc.source
                target = arc.target
                if (source in shared_pre_set and target in mapped_start_places) \
                        or (source in mapped_start_places and target in shared_post_set): \
                        pn_util.remove_arc(subnet_net, arc)
            for node in shared_pre_set:
                add_arc_from_to(node, new_source, subnet_net)
            for node in shared_post_set:
                add_arc_from_to(new_source, node, subnet_net)
            for p in mapped_start_places:
                add_arc_from_to(new_silent, p, subnet_net)
            add_arc_from_to(new_source, new_silent, subnet_net)
            start_place = new_source
    else:
        start_place = node_map[start_places[0]]

    if len(end_places) > 1:
        shared_pre_set = set(pn_util.pre_set(node_map[end_places[0]]))
        len_pre_set_first = len(shared_pre_set)
        for p in end_places[1:]:
            shared_pre_set &= set(pn_util.pre_set(node_map[p]))
        shared_post_set = set(pn_util.post_set(node_map[end_places[0]]))
        len_post_set_first = len(shared_post_set)
        for p in end_places[1:]:
            shared_post_set &= set(pn_util.post_set(node_map[p]))

        if len_pre_set_first == len(shared_pre_set) and len_post_set_first == len(shared_post_set):
            for p in end_places[1:]:
                pn_util.remove_place(subnet_net, node_map[p])
            end_place = node_map[end_places[0]]
        else:
            new_silent = PetriNet.Transition(f"silent_end_{next(id_generator())}")
            subnet_net.transitions.add(new_silent)

            new_sink = PetriNet.Place(f"sink_{next(id_generator())}")
            subnet_net.places.add(new_sink)

            arcs = list(subnet_net.arcs)
            mapped_end_places = [node_map[p] for p in end_places]
            for arc in arcs:
                source = arc.source
                target = arc.target
                if (source in shared_pre_set and target in mapped_end_places) \
                        or (source in mapped_end_places and target in shared_post_set): \
                        pn_util.remove_arc(subnet_net, arc)
            for node in shared_pre_set:
                add_arc_from_to(node, new_sink, subnet_net)
            for node in shared_post_set:
                add_arc_from_to(new_sink, node, subnet_net)
            for p in mapped_end_places:
                add_arc_from_to(p, new_silent, subnet_net)

            add_arc_from_to(new_silent, new_sink, subnet_net)

            end_place = new_sink
    else:
        end_place = node_map[end_places[0]]

    if len(start_place.in_arcs) > 0:
        new_id = next(id_generator())
        new_start = PetriNet.Place(name=f"new_start_{new_id}")
        silent_start = PetriNet.Transition(name=f"silent_start{new_id}", label=None)
        subnet_net.places.add(new_start)
        subnet_net.transitions.add(silent_start)
        add_arc_from_to(new_start, silent_start, subnet_net)
        add_arc_from_to(silent_start, start_place, subnet_net)
    else:
        new_start = start_place

    if len(end_place.out_arcs) > 0:
        new_id = next(id_generator())
        new_end = PetriNet.Place(name=f"new_end_{new_id}")
        silent_end = PetriNet.Transition(name=f"silent_end{new_id}", label=None)
        subnet_net.places.add(new_end)
        subnet_net.transitions.add(silent_end)
        add_arc_from_to(end_place, silent_end, subnet_net)
        add_arc_from_to(silent_end, new_end, subnet_net)
    else:
        new_end = end_place

    return subnet_net, new_start, new_end


def create_subnet(net: PetriNet, subnet_transitions: Set[PetriNet.Transition], start_places, end_places) -> Dict:
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

    subnet_net, new_start, new_end = check_and_repair_markings(subnet_net, node_map, start_places, end_places)

    subnet_initial_marking = Marking()
    subnet_initial_marking[new_start] = 1

    subnet_final_marking = Marking()
    subnet_final_marking[new_end] = 1

    return {
        'net': subnet_net,
        'initial_marking': subnet_initial_marking,
        'final_marking': subnet_final_marking
    }


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
