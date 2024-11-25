from pm4py import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils as pn_util


def validate_petri_net(net: PetriNet, initial_marking: Marking, final_marking: Marking):
    from pm4py.algo.analysis.workflow_net import algorithm as wf_eval

    if not wf_eval.apply(net):
        print(net)
        raise ValueError('The Petri net provided is not a WF-net')

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
        raise Exception(f"Initial marking must match all places with no incoming arcs. {places_no_incoming}")

    places_no_outgoing = [p for p in net.places if not p.out_arcs]
    if set(places_no_outgoing) != set(final_marking.keys()):
        raise Exception(f"Final marking must match all places with no outgoing arcs. {places_no_outgoing}")

    return start_place, end_place


def preprocess_net(net: PetriNet, start_place, end_place):
    """
    Preprocess the Petri net by removing silent transitions at the start and end.

    Modifies the net and markings in place.
    """
    if len(net.transitions) < 2:
        return start_place, end_place
    # Preprocess start: remove p -> silent_transition -> p2
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
                start_place = p2
                print(f"Preprocessed start: Removed {start_place} and {transition}, set {p2} as initial marking.")

    # Preprocess end: remove p3 -> silent_transition -> p4
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
                end_place = p3
                print(f"Preprocessed end: Removed {end_place} and {transition}, set {p3} as final marking.")

    return start_place, end_place


def is_silent(transition) -> bool:
    """
    Determine if a transition is silent.

    This function should be implemented based on how silent transitions are represented.
    For example, they might have a specific label like 'tau' or a property flag.
    """
    return transition.label is None
