from pm4py.objects.process_tree.obj import ProcessTree, Operator


def recursively_transform_process_tree(process_tree, stru=None, level=0):
    if stru is None:
        stru = ["```python\nfrom utils.model_generation import ModelGenerator\n\nmodel_generator = ModelGenerator(True, True)\n\n"]

    node_id = str(id(process_tree))

    for child in process_tree.children:
        stru = recursively_transform_process_tree(child, stru, level=level+1)

    if level == 0:
        new = "final_model = "
    else:
        new = "node"+str(node_id)+" = "

    if process_tree.operator is None:
        if process_tree.label is None:
            new += "model_generator.silent_transition()"
        else:
            new += "model_generator.activity('" + process_tree.label + "')"
    else:
        if process_tree.operator == Operator.SEQUENCE:
            new += "model_generator.partial_order(dependencies=["
            for i in range(len(process_tree.children)-1):
                new += "(node"+str(id(process_tree.children[i]))+", node"+str(id(process_tree.children[i+1]))+"), "
            new += "])"
        elif process_tree.operator == Operator.PARALLEL:
            new += "model_generator.partial_order(dependencies=["
            for child in process_tree.children:
                new += "node"+str(id(child))+", "
            new += "])"
        elif process_tree.operator == Operator.XOR:
            new += "model_generator.xor("
            for child in process_tree.children:
                new += "node"+str(id(child))+", "
            new += ")"
        elif process_tree.operator == Operator.LOOP:
            new += "model_generator.loop("
            for child in process_tree.children:
                new += "node" + str(id(child)) + ", "
            new += ")"

    if new.endswith("= "):
        new += "model_generator.silent_transition()"

    stru.append(new)

    if level == 0:
        stru.append("\n```")
        return "\n".join(stru)
    else:
        return stru
