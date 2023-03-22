from pydantic import parse_file_as
from pathlib import Path
from typing import List, Union, Tuple, Optional
from core.models import Category, VideoBase, AllGroups, Segment, Annotation
import numpy as np


def create_order(vb: VideoBase,
                 labels_ticked_all: Optional[List[List[str]]] = None):
    """Create the order in which videos will be shown."""
    print(f"Currently ticked labels: \n{labels_ticked_all}")

    idx_all = np.arange(len(vb.segments))
    
    # Random permutation if the ticked labels were not provided
    if labels_ticked_all is None:
        return np.random.permutation(idx_all), len(vb.segments), 0
    
    # If no labels were ticked, put the unlabelled segments first
    if len(labels_ticked_all) == 0:
        is_not_labelled = ~np.array(vb.segments_have_annotations())
        n_total_seg = len(is_not_labelled)
        print(f"Total segments: {n_total_seg}")
        n_unlabelled = is_not_labelled.sum()
        print(f"Currently unlabelled: {n_unlabelled}")
        idx_not_labelled = np.random.permutation(idx_all[is_not_labelled])
        idx_labelled = np.random.permutation(idx_all[~is_not_labelled])
        order = np.append(idx_not_labelled, idx_labelled)
        return order, n_total_seg, n_total_seg - n_unlabelled
    
    # If some labels were ticked, put them first
    else:
        labels_ticked_all = [l[1] for l in labels_ticked_all]
        labels_are_ticked = np.vstack([vb.label_in_segments(label) for label in labels_ticked_all])
        any_label_ticked = np.any(labels_are_ticked, axis=0)
        n_total_seg = len(any_label_ticked)
        print(f"Total segments: {n_total_seg}")
        n_with_ticked = any_label_ticked.sum()
        print(f"Currently with the ticked labels: {n_with_ticked}")
        # Create the new order, ticked element first
        idx_ticked = np.random.permutation(idx_all[any_label_ticked])
        idx_not_ticked = np.random.permutation(idx_all[~any_label_ticked])

        order = np.append(idx_ticked, idx_not_ticked)
        return order, n_total_seg, n_with_ticked
 

def load_videobase(json_path: Union[Path, str]):
    vb = parse_file_as(VideoBase, json_path)
    return vb


def load_labels(json_path: Union[Path, str]):
    categories = parse_file_as(AllGroups, json_path)
    groups = categories.groups
    return groups


def find_category(categories: List[Category], category: str) -> Union[Tuple[int, Category], None]:
    """
    Find a category, and its index, by its name

    Parameters
    ----------
    categories: List[Category]
    category: str

    Returns
    -------
    ix: int
    cat: Category
    """
    for ix, cat in enumerate(categories):
        if cat.name == category:
            return ix, cat
    return None


def create_label(categories: List[Category], category: str, label: str) -> List[Category]:
    """
    Add a label to a given category. Creates the category if needed.
    Avoids duplicating labels in the same category

    Parameters
    ----------
    categories: List[Category]
    category: str
        Name of the category to add to
    label: str

    Returns
    -------
    cat: List[Category]

    """
    match = find_category(categories, category)
    if match is None:
        categories.append(Category(name=category, labels=[label]))
        return categories
    ix, cat = match
    if label not in cat.labels:
        cat.labels.append(label)
        categories[ix] = cat
    return categories


def find_label_category(categories: List[Category], label: str) -> Union[None, Tuple[int, Category]]:
    """
    Find to which category a label belongs, if any

    Parameters
    ----------
    categories: List[Category]
    label: str

    Returns
    -------
    ix: int
        Index of category in the given list
    cat: Category or None
    """
    for ix, cat in enumerate(categories):
        if label in cat.labels:
            return ix, cat
    return None


def create_annotation(segment: Segment, user: str, date: str, label: str):
    """
    Add a label to a given segment. Either to an existing annotation session or to a new one

    Parameters
    ----------
    segment: Segment
    user: str
    date: str
    label: str

    Returns
    -------
    segment: models.Segment
        Updated segment
    """
    m_an = None
    for an in segment.annotations:
        if an.user == user and an.date == date:
            m_an = an
            break
    if m_an is None:
        m_an = Annotation(user=user, date=date, labels=[label])
        segment.annotations.append(m_an)
    else:
        # Plays on the reference to the item
        if label not in m_an.labels:
            m_an.labels.append(label)
    return segment


def remove_annotation(segment: Segment, user: str, label: str):
    """
    Remove a label from a segment. Do it in a user specific manner

    Parameters
    ----------
    segment
    user
    label

    Returns
    -------

    """
    m_an = None
    for an in segment.annotations:
        if an.user == user:
            m_an = an
            break
    if m_an is None:
        # No previous annotation was found, no need to remove anything
        return segment
    if label not in m_an.labels:
        # This label is not present, can not remove it
        return segment
    m_an.labels.remove(label)
    return segment


def find_segments_label(vb: VideoBase, label: str) -> List[Segment]:
    """
    Find all segments annotate with a given label
     
    Parameters
    ----------
    vb: VideoBase
    label: str

    Returns
    -------
    matched: List[Segment]
    """
    matched: List[Segment] = []
    if vb is None:
        return matched
    # Could be a long list comprehension. Unrolled for now.
    for seg in vb.segments:
        for an in seg.annotations:
            if label in an.labels:
                matched.append(seg)
    return matched


def rename_label(categories: List[Category], vb: VideoBase,
                 old_label: str, new_label: str) -> Tuple[List[Category], VideoBase]:
    ix, cat = find_label_category(categories, old_label)
    if cat is None:
        raise ValueError(f'{old_label} is not a valid label. Can not be renamed')
    # Replace the label in the category list
    cat.labels = [lb if lb != old_label else new_label for lb in cat.labels]
    # Rename in all previously annotated segments
    segments = find_segments_label(vb, old_label)
    for seg in segments:
        for an in seg.annotations:
            an.labels = [lb if lb != old_label else new_label for lb in an.labels]
    return categories, vb
