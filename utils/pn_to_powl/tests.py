from typing import Union

import pm4py
from pm4py import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils


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

        t = PetriNet.Transition(f"t{i}", f"A {i}")
        net.transitions.add(t)
        add_arc_from_to(end, t, net)

        seq_place = PetriNet.Place(f"seq{i}")
        net.places.add(seq_place)
        add_arc_from_to(t, seq_place, net)

        t2 = PetriNet.Transition(f"t{i}", f"B {i}")
        net.transitions.add(t2)
        add_arc_from_to(seq_place, t2, net)
        add_arc_from_to(t2, parent_place, net)

        t3 = PetriNet.Transition(f"t{i}", f"C {i}")
        net.transitions.add(t3)
        add_arc_from_to(end, t3, net)
        add_arc_from_to(t3, parent_place, net)

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




def test_self_loop():
    net = PetriNet(name="Custom_Petri_Net")

    # Define Places
    source = PetriNet.Place("source")
    p1 = PetriNet.Place("p1")
    B = PetriNet.Place("B")  # Intermediate place after p1
    p2 = PetriNet.Place("p2")
    C = PetriNet.Place("C")
    D = PetriNet.Place("D")
    p3 = PetriNet.Place("p3")
    sink = PetriNet.Place("sink")

    # Add Places to the Petri net
    net.places.update([source, p1, p2, sink])

    # Define Transitions
    trans_A = PetriNet.Transition("A", "A")
    trans_B = PetriNet.Transition("B", "B")
    trans_C = PetriNet.Transition("C", "C")
    trans_D = PetriNet.Transition("D", "D")
    trans_E = PetriNet.Transition("E", "E")

    # Add Transitions to the Petri net
    net.transitions.update([trans_A, trans_B, trans_C, trans_D, trans_E])

    # Add Arcs according to the specified sequence

    # source place -> A
    petri_utils.add_arc_from_to(source, trans_A, net)

    # A -> p1
    petri_utils.add_arc_from_to(trans_A, p1, net)

    # p1 -> B
    petri_utils.add_arc_from_to(p1, trans_E, net)

    # B -> p2
    petri_utils.add_arc_from_to(p1, trans_B, net)
    petri_utils.add_arc_from_to(trans_B, p2, net)

    # p2 -> C
    petri_utils.add_arc_from_to(p2, trans_C, net)

    # p2 -> D
    petri_utils.add_arc_from_to(p2, trans_D, net)

    # C -> p3
    petri_utils.add_arc_from_to(trans_C, p1, net)

    # D -> p3
    petri_utils.add_arc_from_to(trans_D, p1, net)

    # C -> sink
    petri_utils.add_arc_from_to(trans_E, sink, net)

    # Define Initial Marking
    initial_marking = Marking()
    initial_marking[source] = 1  # Token in the source place

    # Define Final Marking
    final_marking = Marking()
    final_marking[sink] = 1

    return net, initial_marking, final_marking


def test_loop_ending_with_par():
    from pm4py.objects.petri_net.obj import PetriNet, Marking
    from pm4py.objects.petri_net.utils import petri_utils

    # Create the Petri net
    net = PetriNet(name="Custom_Petri_Net")

    # Define Places
    source = PetriNet.Place(name="source")
    p1 = PetriNet.Place(name="p1")
    p2 = PetriNet.Place(name="p2")
    p3 = PetriNet.Place(name="p3")
    p4 = PetriNet.Place(name="p4")
    p5 = PetriNet.Place(name="p5")
    sink = PetriNet.Place(name="sink")

    # Add Places to the net
    net.places.add(source)
    net.places.add(p1)
    net.places.add(p2)
    net.places.add(p3)
    net.places.add(p4)
    net.places.add(p5)
    net.places.add(sink)

    # Define Transitions
    A = PetriNet.Transition(name="A", label="A")
    B = PetriNet.Transition(name="B", label="B")
    C = PetriNet.Transition(name="C", label="C")
    D = PetriNet.Transition(name="D", label="D")
    E = PetriNet.Transition(name="E", label="E")
    F = PetriNet.Transition(name="F", label="F")

    # Add Transitions to the net
    net.transitions.add(A)
    net.transitions.add(B)
    net.transitions.add(C)
    net.transitions.add(D)
    net.transitions.add(E)
    net.transitions.add(F)

    # Add Arcs according to the sequence

    # source -> A
    petri_utils.add_arc_from_to(source, A, net)

    # A -> p1
    petri_utils.add_arc_from_to(A, p1, net)

    # p1 -> B
    petri_utils.add_arc_from_to(p1, B, net)

    # B -> p2
    petri_utils.add_arc_from_to(B, p2, net)

    # B -> p3
    petri_utils.add_arc_from_to(B, p3, net)

    # p2 -> C
    petri_utils.add_arc_from_to(p2, C, net)

    # p3 -> D
    petri_utils.add_arc_from_to(p3, D, net)

    # C -> p4
    petri_utils.add_arc_from_to(C, p4, net)

    # D -> p5
    petri_utils.add_arc_from_to(D, p5, net)

    # p4 -> E
    petri_utils.add_arc_from_to(p4, E, net)

    # p5 -> E
    petri_utils.add_arc_from_to(p5, E, net)

    # p4 -> F
    petri_utils.add_arc_from_to(p4, F, net)

    # p5 -> F
    petri_utils.add_arc_from_to(p5, F, net)

    # E -> p1
    petri_utils.add_arc_from_to(E, p1, net)

    # F -> sink
    petri_utils.add_arc_from_to(F, sink, net)

    # Define Initial Marking (source has 1 token)
    initial_marking = Marking()
    initial_marking[source] = 1

    # Define Final Marking (sink has 1 token)
    final_marking = Marking()
    final_marking[sink] = 1

    return net, initial_marking, final_marking


def test_xor_ending_with_par():
    from pm4py.objects.petri_net.obj import PetriNet, Marking
    from pm4py.objects.petri_net.utils import petri_utils

    # Create the Petri net
    net = PetriNet(name="Custom_Petri_Net")

    # Define Places
    source = PetriNet.Place(name="source")
    p1 = PetriNet.Place(name="p1")
    p2 = PetriNet.Place(name="p2")
    p3 = PetriNet.Place(name="p3")
    p4 = PetriNet.Place(name="p4")
    p5 = PetriNet.Place(name="p5")
    sink = PetriNet.Place(name="sink")

    # Add Places to the net
    net.places.add(source)
    net.places.add(p1)
    net.places.add(p2)
    net.places.add(p3)
    net.places.add(p4)
    net.places.add(p5)
    net.places.add(sink)

    # Define Transitions
    A = PetriNet.Transition(name="A", label="A")
    B = PetriNet.Transition(name="B", label="B")
    C = PetriNet.Transition(name="C", label="C")
    D = PetriNet.Transition(name="D", label="D")
    E = PetriNet.Transition(name="E", label="E")
    F = PetriNet.Transition(name="F", label="F")

    # Add Transitions to the net
    net.transitions.add(A)
    net.transitions.add(B)
    net.transitions.add(C)
    net.transitions.add(D)
    net.transitions.add(E)
    net.transitions.add(F)

    # Add Arcs according to the sequence

    # source -> A
    petri_utils.add_arc_from_to(source, A, net)

    # A -> p1
    petri_utils.add_arc_from_to(A, p1, net)

    # p1 -> B
    petri_utils.add_arc_from_to(p1, B, net)

    # B -> p2
    petri_utils.add_arc_from_to(B, p2, net)

    # B -> p3
    petri_utils.add_arc_from_to(B, p3, net)

    # p2 -> C
    petri_utils.add_arc_from_to(p2, C, net)

    # p3 -> D
    petri_utils.add_arc_from_to(p3, D, net)

    # C -> p4
    petri_utils.add_arc_from_to(C, p4, net)

    # D -> p5
    petri_utils.add_arc_from_to(D, p5, net)

    # p4 -> E
    petri_utils.add_arc_from_to(E, p4, net)

    # p5 -> E
    petri_utils.add_arc_from_to(E, p5, net)

    # p4 -> F
    petri_utils.add_arc_from_to(p4, F, net)

    # p5 -> F
    petri_utils.add_arc_from_to(p5, F, net)

    # E -> p1
    petri_utils.add_arc_from_to(p1, E, net)

    # F -> sink
    petri_utils.add_arc_from_to(F, sink, net)

    # Define Initial Marking (source has 1 token)
    initial_marking = Marking()
    initial_marking[source] = 1

    # Define Final Marking (sink has 1 token)
    final_marking = Marking()
    final_marking[sink] = 1

    return net, initial_marking, final_marking


def test_xor_ending_and_starting_with_par():
    from pm4py.objects.petri_net.obj import PetriNet, Marking
    from pm4py.objects.petri_net.utils import petri_utils

    # Create the Petri net
    net = PetriNet(name="Custom_Petri_Net")

    # Define Places
    source = PetriNet.Place(name="source")
    p1 = PetriNet.Place(name="p1")
    p11 = PetriNet.Place(name="p11")
    p2 = PetriNet.Place(name="p2")
    p3 = PetriNet.Place(name="p3")
    p4 = PetriNet.Place(name="p4")
    p5 = PetriNet.Place(name="p5")
    sink = PetriNet.Place(name="sink")

    # Add Places to the net
    net.places.add(source)
    net.places.add(p1)
    net.places.add(p11)
    net.places.add(p2)
    net.places.add(p3)
    net.places.add(p4)
    net.places.add(p5)
    net.places.add(sink)

    # Define Transitions
    A = PetriNet.Transition(name="A", label="A")
    B = PetriNet.Transition(name="B", label="B")
    B2 = PetriNet.Transition(name="B2", label="B2")
    C = PetriNet.Transition(name="C", label="C")
    D = PetriNet.Transition(name="D", label="D")
    E = PetriNet.Transition(name="E", label="E")
    F = PetriNet.Transition(name="F", label="F")

    # Add Transitions to the net
    net.transitions.add(A)
    net.transitions.add(B)
    net.transitions.add(B2)
    net.transitions.add(C)
    net.transitions.add(D)
    net.transitions.add(E)
    net.transitions.add(F)

    # Add Arcs according to the sequence

    # source -> A
    petri_utils.add_arc_from_to(source, A, net)

    # A -> p1
    petri_utils.add_arc_from_to(A, p1, net)
    petri_utils.add_arc_from_to(A, p11, net)

    # p1 -> B
    petri_utils.add_arc_from_to(p1, B, net)
    petri_utils.add_arc_from_to(p11, B2, net)

    # B -> p2
    petri_utils.add_arc_from_to(B, p2, net)




    # B -> p3
    petri_utils.add_arc_from_to(B2, p3, net)

    # p2 -> C
    petri_utils.add_arc_from_to(p2, C, net)

    # p3 -> D
    petri_utils.add_arc_from_to(p3, D, net)

    # C -> p4
    petri_utils.add_arc_from_to(C, p4, net)

    # D -> p5
    petri_utils.add_arc_from_to(D, p5, net)

    # p4 -> E
    petri_utils.add_arc_from_to(E, p4, net)

    # p5 -> E
    petri_utils.add_arc_from_to(E, p5, net)

    # p4 -> F
    petri_utils.add_arc_from_to(p4, F, net)

    # p5 -> F
    petri_utils.add_arc_from_to(p5, F, net)

    # E -> p1
    petri_utils.add_arc_from_to(p1, E, net)
    petri_utils.add_arc_from_to(p11, E, net)

    # F -> sink
    petri_utils.add_arc_from_to(F, sink, net)

    # Define Initial Marking (source has 1 token)
    initial_marking = Marking()
    initial_marking[source] = 1

    # Define Final Marking (sink has 1 token)
    final_marking = Marking()
    final_marking[sink] = 1

    return net, initial_marking, final_marking


def test_loop_ending_with_par2():
    from pm4py.objects.petri_net.obj import PetriNet, Marking
    from pm4py.objects.petri_net.utils import petri_utils

    # Create the Petri net
    net = PetriNet(name="Custom_Petri_Net")

    # Define Places
    source = PetriNet.Place(name="source")
    p1 = PetriNet.Place(name="p1")
    p2 = PetriNet.Place(name="p2")
    p3 = PetriNet.Place(name="p3")
    p4 = PetriNet.Place(name="p4")
    p5 = PetriNet.Place(name="p5")
    sink = PetriNet.Place(name="sink")

    # Add Places to the net
    net.places.add(source)
    net.places.add(p1)
    net.places.add(p2)
    net.places.add(p3)
    net.places.add(p4)
    net.places.add(p5)
    net.places.add(sink)

    # Define Transitions
    A = PetriNet.Transition(name="A", label="A")
    B = PetriNet.Transition(name="B", label="B")
    C = PetriNet.Transition(name="C", label="C")
    D = PetriNet.Transition(name="D", label="D")
    E = PetriNet.Transition(name="E", label="E")
    F = PetriNet.Transition(name="F", label="F")

    # Add Transitions to the net
    net.transitions.add(A)
    net.transitions.add(B)
    net.transitions.add(C)
    net.transitions.add(D)
    net.transitions.add(E)
    net.transitions.add(F)

    # Add Arcs according to the sequence

    # source -> A
    petri_utils.add_arc_from_to(source, A, net)

    # # A -> p1
    # petri_utils.add_arc_from_to(A, p1, net)
    #
    # # p1 -> B
    # petri_utils.add_arc_from_to(p1, B, net)

    # B -> p2
    petri_utils.add_arc_from_to(A, p2, net)

    # B -> p3
    petri_utils.add_arc_from_to(A, p3, net)

    # p2 -> C
    petri_utils.add_arc_from_to(p2, C, net)

    # p3 -> D
    petri_utils.add_arc_from_to(p3, D, net)

    # C -> p4
    petri_utils.add_arc_from_to(C, p4, net)

    # D -> p5
    petri_utils.add_arc_from_to(D, p5, net)

    # p4 -> E
    petri_utils.add_arc_from_to(p4, B, net)

    # p5 -> E
    petri_utils.add_arc_from_to(p5, B, net)

    petri_utils.add_arc_from_to(B, p1, net)

    # p4 -> F
    petri_utils.add_arc_from_to(p1, F, net)

    # p5 -> F
    petri_utils.add_arc_from_to(p1, E, net)

    # E -> p1
    petri_utils.add_arc_from_to(E, p2, net)
    petri_utils.add_arc_from_to(E, p3, net)

    # F -> sink
    petri_utils.add_arc_from_to(F, sink, net)

    # Define Initial Marking (source has 1 token)
    initial_marking = Marking()
    initial_marking[source] = 1

    # Define Final Marking (sink has 1 token)
    final_marking = Marking()
    final_marking[sink] = 1

    return net, initial_marking, final_marking


def test_po():
    # net, initial_marking, final_marking = pm4py.read_pnml(r"C:\Users\kourani\PycharmProjects\EvaluatingLLMsProcessModeling\ground_truth\ground_truth_pn\18.pnml")
    net, initial_marking, final_marking = pm4py.read_pnml(r"C:\Users\kourani\Downloads\trial5.pnml")
    # net, initial_marking, final_marking = pm4py.read_pnml(r"C:\Users\kourani\Downloads\beast.pnml")
    # tree = pm4py.convert_to_process_tree(net, initial_marking, final_marking)
    # pm4py.view_process_tree(tree, format="SVG")
    return net, initial_marking, final_marking