# Sources and licensing

The MIT license in `LICENSE` covers Quantum Motif's original Python code,
tests, documentation and synthetic fixtures. It does not relicense the
music21 corpus, third-party packages, source editions or derived Bach data.

The real-data command uses Johann Sebastian Bach's chorale harmonizations
from the Riemenschneider collection exposed by `music21.corpus.chorales.Iterator`.
The underlying compositions and their digital editions are separate works
for attribution and licensing purposes. music21 credits Margaret Greentree
for permission to distribute her edited MusicXML Bach chorale collection.
See [music21 authors and licensing](https://music21.org/music21docs/about/about.html)
and [chorale collection documentation](https://music21.org/music21docs/moduleReference/moduleCorpusChorales.html).

music21's BSD license covers its software, excluding corpus encodings. Its
corpus notice says that encoded works are distributed with permission where
needed; individual works can carry noncommercial or other restrictions.
Consult the source file and its embedded notices for any reuse. Our outputs
retain original corpus paths, source-file SHA-256 hashes, embedded MusicXML
creator/rights entries, and source/group/bar provenance in `report.json` and
`motifs.jsonl`. We make no blanket MIT or public-domain claim for these editions
or derived data. Raw MusicXML files are not copied into the deliverables.

The installed package dependency licenses remain with their respective
authors. Qiskit provides the circuit and Statevector implementation; NumPy
provides numerical routines; mido writes MIDI; music21 supplies corpus parsing
and key analysis; Qiskit Algorithms supplies SPSA optimization; pytest supplies verification. Exact installed versions are
recorded in `uv.lock` and generated reports.

The original generated demo uses random, untrained circuit parameters and
directly decoded outcomes. Milestone 2's separate audio uses fitted checkpoints
trained on the attributed Bach-derived motifs. Those outputs retain checkpoint
and dataset provenance and should be considered with the corpus notices above.
Neither demonstration establishes quantum advantage or final generalization.
