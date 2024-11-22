from typing import Union

import pm4py
from pm4py import PetriNet, Marking


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


def test_base_case():
    print("=== Testing Base Case ===")
    net, initial_marking, final_marking = create_simple_petri_net()
    return net, initial_marking, final_marking
def create_simple_petri_net() -> (PetriNet, Marking, Marking):
    """
    Create a simple Petri net with one transition (base case).

    Returns:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking
    """
    net = PetriNet("Simple Net")
    start = PetriNet.Place("start")
    end = PetriNet.Place("end")
    net.places.add(start)
    net.places.add(end)

    t1 = PetriNet.Transition("t1", "Do something")
    net.transitions.add(t1)

    add_arc_from_to(start, t1, net)
    add_arc_from_to(t1, end, net)

    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[start] = 1
    final_marking[end] = 1

    return net, initial_marking, final_marking


def test_choice(n=5) -> (PetriNet, Marking, Marking):
    """
    Create a Petri net with an XOR split into n base case subnets.

    Parameters:
    - n: Number of choices

    Returns:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking
    """
    net = PetriNet("Enhanced Choice Net with Silent Transitions")

    # Define places
    start = PetriNet.Place("start")
    end = PetriNet.Place("end")
    net.places.add(start)
    net.places.add(end)

    # Create main transition from start to main choice places
    t_main = PetriNet.Transition("t_main", None)
    net.transitions.add(t_main)
    add_arc_from_to(start, t_main, net)

    # Create n main choice places (p1 to pn)
    main_choice_place = PetriNet.Place("p")
    net.places.add(main_choice_place)
    add_arc_from_to(t_main, main_choice_place, net)

    # For the first two main choices, add secondary choices using silent transitions
    for i in range(1, 3):  # Assuming you want to add secondary choices to the first two places
        parent_place = main_choice_place

        # Create a silent transition for splitting
        s = PetriNet.Transition(f"s{i}", None)
        net.transitions.add(s)
        add_arc_from_to(parent_place, s, net)

        # Create an intermediate place between silent transition and sub-transitions
        intermediate_p = PetriNet.Place(f"intermediate_p{i}")
        net.places.add(intermediate_p)
        add_arc_from_to(s, intermediate_p, net)

        # Create sub-choice transitions (t1_1 to t1_n and t2_1 to t2_n)
        for j in range(1, n + 1):
            sub_t = PetriNet.Transition(f"t{i}_{j}", f"Action {i}_{j}")
            net.transitions.add(sub_t)
            add_arc_from_to(intermediate_p, sub_t, net)
            add_arc_from_to(sub_t, end, net)
        sub_t = PetriNet.Transition(f"t{i}_silent", None)
        net.transitions.add(sub_t)
        add_arc_from_to(intermediate_p, sub_t, net)
        add_arc_from_to(sub_t, end, net)


    # For the remaining main choice places, connect directly to end via their transitions
    for i in range(3, n + 1):
        parent_place = main_choice_place
        t = PetriNet.Transition(f"t{i}", f"Action {i}")
        net.transitions.add(t)
        add_arc_from_to(parent_place, t, net)

        seq_place = PetriNet.Place(f"seq{i}")
        net.places.add(seq_place)
        add_arc_from_to(t, seq_place, net)

        t2 = PetriNet.Transition(f"t{i}", f"after Action {i}")
        net.transitions.add(t2)
        add_arc_from_to(seq_place, t2, net)
        add_arc_from_to(t2, end, net)

    parent_place = main_choice_place
    t = PetriNet.Transition(f"SILENT", None)
    net.transitions.add(t)
    add_arc_from_to(parent_place, t, net)
    add_arc_from_to(t, end, net)

    second_endt = PetriNet.Transition(f"second_end_t", None)
    net.transitions.add(second_endt)

    second_endp = PetriNet.Place(f"second_end_p")
    net.places.add(second_endp)

    add_arc_from_to(end, second_endt, net)
    add_arc_from_to(second_endt, second_endp, net)

    # Define initial and final markings
    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[start] = 1
    final_marking[second_endp] = 1

    return net, initial_marking, final_marking


def test_choice2(n=5) -> (PetriNet, Marking, Marking):
    """
    Create a Petri net with an XOR split into n base case subnets.

    Parameters:
    - n: Number of choices

    Returns:
    - net: PetriNet
    - initial_marking: Marking
    - final_marking: Marking
    """
    net = PetriNet("Enhanced Choice Net with Silent Transitions")

    # Define places
    start = PetriNet.Place("start")
    end = PetriNet.Place("end")
    net.places.add(start)
    net.places.add(end)

    # Create main transition from start to main choice places
    t_main = PetriNet.Transition("t_main", None)
    net.transitions.add(t_main)
    add_arc_from_to(start, t_main, net)

    # Create n main choice places (p1 to pn)
    main_choice_place = PetriNet.Place("p")
    net.places.add(main_choice_place)
    add_arc_from_to(t_main, main_choice_place, net)

    # For the first two main choices, add secondary choices using silent transitions
    for i in range(1, 3):  # Assuming you want to add secondary choices to the first two places
        parent_place = main_choice_place

        intermediate_p2 = PetriNet.Place(f"intermediate_p2{i}")
        net.places.add(intermediate_p2)

        # Create sub-choice transitions (t1_1 to t1_n and t2_1 to t2_n)
        for j in range(1, n + 1):
            sub_t = PetriNet.Transition(f"t{i}_{j}", f"Action {i}_{j}")
            net.transitions.add(sub_t)
            add_arc_from_to(parent_place, sub_t, net)
            add_arc_from_to(sub_t, intermediate_p2, net)
        sub_t = PetriNet.Transition(f"t{i}_silent", None)
        net.transitions.add(sub_t)
        add_arc_from_to(parent_place, sub_t, net)
        add_arc_from_to(sub_t, intermediate_p2, net)

        new_silent = PetriNet.Transition(f"silent_new_{i}")
        net.transitions.add(new_silent)
        add_arc_from_to(intermediate_p2, new_silent, net)
        add_arc_from_to(new_silent, end, net)



    # For the remaining main choice places, connect directly to end via their transitions
    for i in range(3, n + 1):
        parent_place = main_choice_place
        t = PetriNet.Transition(f"t{i}", f"Action {i}")
        net.transitions.add(t)
        add_arc_from_to(parent_place, t, net)

        seq_place = PetriNet.Place(f"seq{i}")
        net.places.add(seq_place)
        add_arc_from_to(t, seq_place, net)

        t2 = PetriNet.Transition(f"t{i}", f"after Action {i}")
        net.transitions.add(t2)
        add_arc_from_to(seq_place, t2, net)
        add_arc_from_to(t2, end, net)

    parent_place = main_choice_place
    t = PetriNet.Transition(f"SILENT", None)
    net.transitions.add(t)
    add_arc_from_to(parent_place, t, net)
    add_arc_from_to(t, end, net)

    second_endt = PetriNet.Transition(f"second_end_t", None)
    net.transitions.add(second_endt)

    second_endp = PetriNet.Place(f"second_end_p")
    net.places.add(second_endp)

    add_arc_from_to(end, second_endt, net)
    add_arc_from_to(second_endt, second_endp, net)

    # Define initial and final markings
    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[start] = 1
    final_marking[second_endp] = 1

    return net, initial_marking, final_marking

def test_loop(n=5):
    net = PetriNet("Enhanced Choice Net with Silent Transitions")

    # Define places
    start = PetriNet.Place("start")
    end = PetriNet.Place("end")
    net.places.add(start)
    net.places.add(end)

    # Create main transition from start to main choice places
    t_main = PetriNet.Transition("t_main", None)
    net.transitions.add(t_main)
    add_arc_from_to(start, t_main, net)

    # Create n main choice places (p1 to pn)
    main_choice_place = PetriNet.Place("p")
    net.places.add(main_choice_place)
    add_arc_from_to(t_main, main_choice_place, net)

    # For the first two main choices, add secondary choices using silent transitions
    for i in range(1, 3):  # Assuming you want to add secondary choices to the first two places
        parent_place = main_choice_place

        # Create a silent transition for splitting
        s = PetriNet.Transition(f"s{i}", None)
        net.transitions.add(s)
        add_arc_from_to(parent_place, s, net)

        # Create an intermediate place between silent transition and sub-transitions
        intermediate_p = PetriNet.Place(f"intermediate_p{i}")
        net.places.add(intermediate_p)
        add_arc_from_to(s, intermediate_p, net)

        intermediate_p2 = PetriNet.Place(f"intermediate2_p{i}")
        net.places.add(intermediate_p2)

        # Create sub-choice transitions (t1_1 to t1_n and t2_1 to t2_n)
        for j in range(1, n + 1):
            sub_t = PetriNet.Transition(f"t{i}_{j}", f"Action {i}_{j}")
            net.transitions.add(sub_t)
            add_arc_from_to(intermediate_p, sub_t, net)
            add_arc_from_to(sub_t, intermediate_p2, net)
        sub_t = PetriNet.Transition(f"t{i}_silent", None)
        net.transitions.add(sub_t)
        add_arc_from_to(intermediate_p, sub_t, net)
        add_arc_from_to(sub_t, intermediate_p2, net)

        sub_t2 = PetriNet.Transition(f"final", None)
        net.transitions.add(sub_t2)

        add_arc_from_to(intermediate_p2, sub_t2, net)
        add_arc_from_to(sub_t2, end, net)

    # For the remaining main choice places, connect directly to end via their transitions
    for i in range(3, n + 1):
        parent_place = main_choice_place
        t = PetriNet.Transition(f"t{i}", f"Action {i}")
        net.transitions.add(t)
        add_arc_from_to(end, t, net)

        seq_place = PetriNet.Place(f"seq{i}")
        net.places.add(seq_place)
        add_arc_from_to(t, seq_place, net)

        t2 = PetriNet.Transition(f"t{i}", f"after Action {i}")
        net.transitions.add(t2)
        add_arc_from_to(seq_place, t2, net)
        add_arc_from_to(t2, parent_place, net)

    parent_place = main_choice_place
    t = PetriNet.Transition(f"SILENT", None)
    net.transitions.add(t)
    add_arc_from_to(parent_place, t, net)
    add_arc_from_to(t, end, net)

    second_endt = PetriNet.Transition(f"second_end_t", None)
    net.transitions.add(second_endt)

    second_endp = PetriNet.Place(f"second_end_p")
    net.places.add(second_endp)

    add_arc_from_to(end, second_endt, net)
    add_arc_from_to(second_endt, second_endp, net)

    # Define initial and final markings
    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[start] = 1
    final_marking[second_endp] = 1

    return net, initial_marking, final_marking


def test_simple_loop(n=5):
    net = PetriNet("Minimal Loop Workflow Net")

    # Define places
    p_start = PetriNet.Place("p_start")
    p1 = PetriNet.Place("p1")
    p11 = PetriNet.Place("p11")
    p_end = PetriNet.Place("p_end")
    net.places.update([p_start, p1, p11, p_end])

    # Define transitions
    t1 = PetriNet.Transition("t1", None)
    t2 = PetriNet.Transition("t2", "Action 2")  # Loop transition
    t22 = PetriNet.Transition("t22", "Action 3")
    t3 = PetriNet.Transition("t3", None)
    net.transitions.update([t1, t2, t22, t3])

    # Add arcs
    add_arc_from_to(p_start, t1, net)
    add_arc_from_to(t1, p1, net)
    add_arc_from_to(p1, t2, net)
    add_arc_from_to(t2, p11, net)
    add_arc_from_to(p11, t22, net)
    add_arc_from_to(t22, p1, net)
    # Loop back to p1
    add_arc_from_to(p11, t3, net)
    add_arc_from_to(t3, p_end, net)

    # Define initial and final markings
    initial_marking = Marking()
    final_marking = Marking()
    initial_marking[p_start] = 1
    final_marking[p_end] = 1

    return net, initial_marking, final_marking