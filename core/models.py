from typing import List, Optional
from pydantic import BaseModel, root_validator, ValidationError


class Frames(BaseModel):
    begin: int
    end: int

    @root_validator
    def begin_smaller(cls, values):
        b, e = values.get('begin'), values.get('end')
        if b >= e:
            raise ValidationError('First frame of fragment should come before last frame')
        return values


class Annotation(BaseModel):
    user: str
    date: str
    labels: List[str]

    def label_in_annotation(self, label):
        "Return True if the input label is in the annotations."
        return label in self.labels


class Segment(BaseModel):
    subject: str
    date: str
    session: str
    uid: str
    folder: str
    files: List[str]
    frames: Frames
    annotations: List[Annotation]
    
    def has_annotations(self) -> bool:
        "Return True the segment has annotations."
        return len(self.annotations) > 0
    
    def label_in_segment(self, label: str) -> bool:
        "Return True if any of the annotations has the input label."
        if self.has_annotations():
            return any(a.label_in_annotation(label) for a in self.annotations)
        else:
            return False


class VideoBase(BaseModel):
    segments: List[Segment]
    notes: Optional[str]
    
    def segments_have_annotations(self) -> List[bool]:
        "Return a list of bool indicating if the segments are annotated."
        return [s.has_annotations() for s in self.segments]
    
    def label_in_segments(self, label: str) -> List[bool]:
        "Return a list of bool indicating if each segment has an input label."
        return [s.label_in_segment(label) for s in self.segments]


class Category(BaseModel):
    name: str
    labels: List[str]


class AllGroups(BaseModel):
    groups: List[Category]


if __name__ == '__main__':
    frames = Frames(begin=12, end=50)
    an = Annotation(user='Ghyomm', date='01/04/2022', labels=['grooming', 'scratching'])
    seg = Segment(subject='RF484', date='01/04/2022', session='test', uid='RF484_220401_test',
                  folder='.', files=['f1.avi', 'f2.avi', 'f3.avi', 'f4.avi', 'f5.avi'],
                  frames=frames, annotations=[an])
    vb = VideoBase(segments=[seg] * 3)
    with open('schema.json', 'w') as jf:
        jf.write(vb.json(indent=2))

    g1 = Category(name='cleaning', labels=['grooming', 'scratching'])
    g2 = Category(name='moving', labels=['running'])
    ag = AllGroups(groups=[g1, g2])
    with open('labels.json', 'w') as jf:
        jf.write(ag.json(indent=2))

