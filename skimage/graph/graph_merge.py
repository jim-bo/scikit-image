import numpy as np
import heapq


def _hmerge_mean_color(graph, src, dst, n):
    """Callback to handle merging nodes by recomputing mean color.

    The method expects that the mean color of `dst` is already computed.

    Parameters
    ----------
    graph : RAG
        The graph under consideration.
    src, dst : int
        The vertices in `graph` to be merged.
    n : int
        A neighbor of `src` or `dst` or both.

    Returns
    -------
    weight : float
        The absolute difference of the mean color between node `dst` and `n`.
    """
    diff = graph.node[dst]['mean color'] - graph.node[n]['mean color']
    diff = np.linalg.norm(diff)
    return diff


def _revalidate_node_edges(rag, node, heap_list):
    """Handles validation and invalidation of edges incident to a node.

    This function invalidates all existing edges incident on `node` and inserts
    new items in `heap_list` updated with the valid weights.

    rag : RAG
        The Region Adjacency Graph.
    node : int
        The id of the node whose incident edges are to be validated/invalidated
        .
    heap_list : list
        The list containing the existing heap of edges.
    """
    # networkx updates data dictionary if edge exists
    # this would mean we have to reposition these edges in
    # heap if their weight is updated.
    # instead we invalidate them

    for n in rag.neighbors(node):
        data = rag[node][n]
        try:
            # invalidate existing neghbors of `dst`, they have new weights
            data['heap item'][3] = False
        except KeyError:
            # will hangle the case where the edge did not exist in the existing
            # graph
            pass

        wt = data['weight']
        heap_item = [wt, node, n, True]
        data['heap item'] = heap_item
        heapq.heappush(heap_list, heap_item)


def merge_hierarchical(labels, rag, thresh, in_place=True):
    """Perform hierarchical merging of a RAG.

    Greedily merges the most similar pair of nodes until no edges lower than
    `thresh` remain.

    Parameters
    ----------
    labels : ndarray
        The array of labels.
    rag : RAG
        The Region Adjacency Graph.
    thresh : float
        Regions connected by an edge with weight smaller than `thresh` are
        merged.
    in_place : bool, optional
        If set, the RAG is modified in place.

    Returns
    -------
    out : ndarray
        The new labeled array.

    Examples
    --------
    >>> from skimage import data, graph, segmentation
    >>> img = data.coffee()
    >>> labels = segmentation.slic(img)
    >>> rag = graph.rag_mean_color(img, labels)
    >>> new_labels = graph.merge_hierarchical(labels, rag, 40)
    """
    if not in_place:
        rag = rag.copy()

    edge_heap = []
    for src, dst, data in rag.edges_iter(data=True):
        # Push a valid edge in the heap
        wt = data['weight']
        heap_item = [wt, src, dst, data]
        heapq.heappush(edge_heap, heap_item)

        # Reference to the heap item in the graph
        data['heap item'] = heap_item

    while edge_heap[0][0] < thresh:
        _, src, dst, valid = heapq.heappop(edge_heap)

        # Ensure popped edge is valid, if not, the edge is discarded
        if valid:
            rag.node[dst]['total color'] += rag.node[src]['total color']
            rag.node[dst]['pixel count'] += rag.node[src]['pixel count']
            rag.node[dst]['mean color'] = (rag.node[dst]['total color'] /
                                           rag.node[dst]['pixel count'])

            # Invalidate all neigbors of `src` before its deleted
            for n in rag.neighbors(src):
                rag[src][n]['heap item'][3] = False

            rag.merge_nodes(src, dst, _hmerge_mean_color)
            _revalidate_node_edges(rag, dst, edge_heap)

    arr = np.arange(labels.max() + 1)
    for ix, (n, d) in enumerate(rag.nodes_iter(data=True)):
        for label in d['labels']:
            arr[label] = ix

    return arr[labels]
