import pm4py
from pm4py import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util
from pm4py.algo.analysis.workflow_net import algorithm as wf_eval


def validate_petri_net(net: PetriNet, initial_marking: Marking, final_marking: Marking):
    if len(initial_marking) != 1:
        raise Exception(f"Initial marking must consist of exactly one place: {initial_marking}")

    if len(final_marking) != 1:
        raise Exception(f"Final marking must consist of exactly one place: {final_marking}")

    start_place = list(initial_marking.keys())[0]
    end_place = list(final_marking.keys())[0]

    if initial_marking[start_place] != 1:
        raise Exception(f"Number of tokens in initial marking must be 1!")

    if final_marking[end_place] != 1:
        raise Exception(f"Number of tokens in final marking must be 1!")

    if start_place not in net.places or end_place not in net.places:
        raise Exception(f"Start or end place in the Petri net!")

    places_no_incoming = [p for p in net.places if not p.in_arcs]
    if set(places_no_incoming) != set(initial_marking.keys()):
        pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")
        raise Exception(f"Initial marking must match all places with no incoming arcs. {places_no_incoming}")

    places_no_outgoing = [p for p in net.places if not p.out_arcs]
    if set(places_no_outgoing) != set(final_marking.keys()):
        pm4py.view_petri_net(net, initial_marking, final_marking, format="SVG")
        raise Exception(f"Final marking must match all places with no outgoing arcs. {net}")

    if not wf_eval.apply(net):
        raise ValueError('The Petri net provided is not a WF-net')

    return start_place, end_place


def preprocess_net(net: PetriNet, start_place, end_place):
    if len(net.transitions) < 2:
        return {start_place}, {end_place}

    # Preprocess start: remove p -> silent_transition -> p2
    start_places = {start_place}
    end_places = {end_place}
    successors = list(pn_util.post_set(start_place))
    if len(successors) == 1:
        transition = successors[0]
        if is_silent(transition):
            pn_util.remove_place(net, start_place)
            start_places.remove(start_place)
            next_places = list(pn_util.post_set(transition))
            pn_util.remove_transition(net, transition)

            for p in next_places:
                start_places.add(p)

    # Preprocess end: remove p3 -> silent_transition -> p4
    if len(net.transitions) > 1:
        predecessors = list(pn_util.pre_set(end_place))
        if len(predecessors) == 1:
            transition = predecessors[0]
            if is_silent(transition):
                pn_util.remove_transition(net, transition)
                pn_util.remove_place(net, end_place)
                end_places.remove(end_place)
                prev_places = list(pn_util.pre_set(transition))
                for p in prev_places:
                    end_places.add(p)

    places = list(net.places)
    for p in places:
        if len(p.in_arcs) == 0 == len(p.out_arcs):
            pn_util.remove_place(net, p)
            start_places.remove(p)
            end_places.remove(p)

    return start_places, end_places


def remove_duplicate_places(net: PetriNet, start_places, end_places):
    start_places = list(start_places)
    end_places = list(end_places)

    start_places_to_keep = {start_places[0]}
    for place in start_places[1:]:
        if any(pn_util.post_set(place) == pn_util.post_set(other)
               and pn_util.pre_set(place) == pn_util.pre_set(other)
               for other in start_places_to_keep):
            pn_util.remove_place(net, place)
        else:
            start_places_to_keep.add(place)

    end_places_to_keep = {end_places[0]}
    for place in end_places[1:]:
        if any(pn_util.post_set(place) == pn_util.post_set(other)
               and pn_util.pre_set(place) == pn_util.pre_set(other)
               for other in end_places_to_keep):
            pn_util.remove_place(net, place)
        else:
            end_places_to_keep.add(place)

    return start_places_to_keep, end_places_to_keep


def is_silent(transition) -> bool:
    return transition.label is None
