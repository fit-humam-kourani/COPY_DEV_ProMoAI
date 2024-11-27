from collections import deque, defaultdict

import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
import re

from pm4py.objects.petri_net.utils.reachability_graph import marking_flow_petri
from pm4py.objects.transition_system import obj as ts


def get_reachable_transitions_from_marking_to_another(im: Marking, fm: Marking, map_states, transition_map):
    i_state = map_states[im]
    f_state = map_states[fm]

    reachable_transitions = set()

    # Step 1: Backward BFS to find all states that can reach fm
    reachable_states_from_fm = set()
    backward_queue = deque([f_state])
    while backward_queue:
        current_state = backward_queue.popleft()
        if current_state not in reachable_states_from_fm:
            reachable_states_from_fm.add(current_state)
            for incoming_transition in current_state.incoming:
                from_state = incoming_transition.from_state
                backward_queue.append(from_state)

    # Step 2: Forward BFS from im, only considering transitions leading to reachable states
    forward_queue = deque(i_state.outgoing)
    while forward_queue:
        transition = forward_queue.popleft()
        if transition not in reachable_transitions:
            to_state = transition.to_state
            if to_state in reachable_states_from_fm:
                reachable_transitions.add(transition)
                if to_state != f_state:
                    forward_queue.extend(to_state.outgoing)

    return {transition_map[elm] for elm in reachable_transitions}


def __add_arc_from_to_ts(t_map, pn_transition, fr, to, tsys, data=None):
    tran = pm4py.objects.transition_system.obj.TransitionSystem.Transition(repr(pn_transition), fr, to, data)
    tsys.transitions.add(tran)
    fr.outgoing.add(tran)
    to.incoming.add(tran)
    t_map[tran] = pn_transition
    return t_map


def generate_reachability_graph(net, im):
    incoming_transitions, outgoing_transitions, eventually_enabled = marking_flow_petri(net, im)

    re_gr = ts.TransitionSystem()

    map_states = {}
    transition_map = {}
    for s in incoming_transitions:
        map_states[s] = ts.TransitionSystem.State(__state_rep(repr(s)))
        re_gr.states.add(map_states[s])

    for s1 in outgoing_transitions:
        for t in outgoing_transitions[s1]:
            s2 = outgoing_transitions[s1][t]
            __add_arc_from_to_ts(transition_map, t, map_states[s1], map_states[s2], re_gr)

    res = __find_reachable_petri_transitions_per_ts_transition(transition_map)
    return res, map_states, transition_map


def __state_rep(name):
    return re.sub(r'\W+', '', name)


def __find_reachable_petri_transitions_per_ts_transition(transition_map):
    petri_to_reach = defaultdict(set)
    for reach_tr, petri_tr in transition_map.items():
        petri_to_reach[petri_tr].add(reach_tr)

    petri_reachable = defaultdict(set)
    ts_reachable = defaultdict(set)

    reach_tr_reachable_cache = {}

    for petri_tr, reach_tr_set in petri_to_reach.items():
        reachable_petri = set()

        for reach_tr in reach_tr_set:
            if reach_tr in reach_tr_reachable_cache:
                reachable_petri.update(reach_tr_reachable_cache[reach_tr])
                continue

            start_state = reach_tr.to_state
            queue = deque(start_state.outgoing)
            visited_reach_tr = set()
            local_reachable_petri = set()

            while queue:
                current_tr = queue.popleft()
                if current_tr not in visited_reach_tr:
                    visited_reach_tr.add(current_tr)
                    mapped_petri_tr = transition_map.get(current_tr)
                    if mapped_petri_tr:
                        local_reachable_petri.add(mapped_petri_tr)
                    queue.extend(current_tr.to_state.outgoing)

            reach_tr_reachable_cache[reach_tr] = local_reachable_petri

            reachable_petri.update(local_reachable_petri)
            ts_reachable[reach_tr] = local_reachable_petri

        reachable_petri.add(petri_tr)
        petri_reachable[petri_tr] = reachable_petri

    return ts_reachable


def transitions_always_reachable_from_each_other(t1: PetriNet.Transition,
                                                 t2: PetriNet.Transition,
                                                 transition_map,
                                                 reachable_ts_transitions_dict):
    ts_1 = {t for t in transition_map.keys() if transition_map[t] == t1}
    ts_2 = {t for t in transition_map.keys() if transition_map[t] == t2}
    for t in ts_1:
        if t2 not in reachable_ts_transitions_dict[t]:
            return False
    for t in ts_2:
        if t1 not in reachable_ts_transitions_dict[t]:
            return False

    return True


def can_transitions_be_on_same_path(t1: PetriNet.Transition,
                                    t2: PetriNet.Transition,
                                    transition_map,
                                    reachable_ts_transitions_dict):
    for t_ts in reachable_ts_transitions_dict.keys():
        if transition_map[t_ts] == t1:
            if t2 in reachable_ts_transitions_dict[t_ts]:
                return True
        elif transition_map[t_ts] == t2:
            if t1 in reachable_ts_transitions_dict[t_ts]:
                return True

    return False
