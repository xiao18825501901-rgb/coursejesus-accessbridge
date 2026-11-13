from collections import deque
from app.lessons import load_lessons


def test_bfs_order_is_computed_not_copied_from_answer():
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["E"], "D": [], "E": []}
    q = deque(["A"]); seen = {"A"}; order = []
    while q:
        node = q.popleft(); order.append(node)
        for v in sorted(graph[node]):
            if v not in seen: seen.add(v); q.append(v)
    lesson = next(x for x in load_lessons() if x.lesson_id == "bfs-dfs")
    question = lesson.quiz[1]
    assert ", ".join(order) == question.options[question.answer].en


def test_dfs_prefix_has_explicit_tie_break():
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["E"], "D": [], "E": []}
    order = []
    def visit(node):
        order.append(node)
        for v in sorted(graph[node]): visit(v)
    visit("A")
    lesson = next(x for x in load_lessons() if x.lesson_id == "bfs-dfs")
    question = lesson.quiz[2]
    assert "B before C" in question.prompt.en
    assert ", ".join(order[:3]) == question.options[question.answer].en


def test_homogeneous_transform_example():
    def mv(m, v): return tuple(sum(row[k]*v[k] for k in range(3)) for row in m)
    s = ((2,0,0),(0,2,0),(0,0,1))
    r = ((0,-1,0),(1,0,0),(0,0,1))
    t = ((1,0,1),(0,1,1),(0,0,1))
    p = (1,0,1)
    assert mv(t,mv(r,mv(s,p))) == (1,3,1)
    assert mv(s,mv(r,mv(t,p))) == (-2,4,1)
    lesson = next(x for x in load_lessons() if x.lesson_id == "matrix-transform")
    assert "homogeneous" in lesson.original_source_excerpt.en
    assert "not a universal default" in lesson.original_source_excerpt.en
    assert "(-2,4)" in lesson.steps[2].body.en


def test_stack_and_queue_from_operations():
    data = list("ABC")
    assert data.pop() == "C"
    queue = deque("ABC")
    assert queue.popleft() == "A"
