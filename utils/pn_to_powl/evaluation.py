import pm4py
from pm4py.algo.simulation.tree_generator.algorithm import apply as tree_gen
from pm4py.objects.powl.obj import POWL

from utils.pn_to_powl.converter import convert_workflow_net_to_powl


def get_leaves(model: POWL):
    if model.children:
        res = []
        for child in model.children:
            res = res + get_leaves(child)
        return res
    else:
        if model.label:
            return [model]
        else:
            return []


tree = tree_gen(parameters={"min": 10, "mode": 250, "max": 500})
pn, im, fm = pm4py.convert_to_petri_net(tree)
powl_model = convert_workflow_net_to_powl(pn, im, fm)
print(len(pn.transitions))
print(len([t for t in pn.transitions if t.label]))
print(len(pn.places))
print(len(pn.arcs))
print(len(get_leaves(powl_model)))
