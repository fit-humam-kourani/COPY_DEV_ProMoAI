from collections import deque
import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
import re
from pm4py.objects.petri_net.utils.reachability_graph import marking_flow_petri
from pm4py.objects.transition_system import obj as ts


def get_reachable_transitions_from_marking_to_another(im: Marking, fm: Marking, map_states, transition_map):
    i_state = map_states[im]
    f_state = map_states[fm]

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

    reachable_transitions = set()

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


def __find_reachable_petri_transitions_per_ts_transition(map_ts_transition_to_pn_transition):
    reachability_map = {}

    for ts_transition in map_ts_transition_to_pn_transition.keys():

        start_state = ts_transition.to_state
        queue = deque(start_state.outgoing)
        visited_ts_transitions = set()
        local_reachable_pn_transitions = set()

        while queue:
            current_tr = queue.popleft()
            if current_tr not in visited_ts_transitions:
                visited_ts_transitions.add(current_tr)
                local_reachable_pn_transitions.add(map_ts_transition_to_pn_transition.get(current_tr))
                queue.extend(current_tr.to_state.outgoing)

        reachability_map[ts_transition] = local_reachable_pn_transitions

    return reachability_map


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
