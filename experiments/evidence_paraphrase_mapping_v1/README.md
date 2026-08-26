# Evidence Paraphrase-Invariant Mapping Experiment V1

Experiment-only evaluation of required-point/evidence matching candidates.
Production Evidence, Retriever, Citation, Answer, and Runtime are not modified.

The runner imports frozen retrieval/evidence components for baseline observation,
then applies candidate scoring only to copied trace data. No candidate output is
fed into production Runtime.
