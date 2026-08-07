# Evidence reports

`unpaid-qualification.json` is generated only from a clean commit by:

```bash
uv run ai-abyss-benchmark unpaid-qualification
```

The command regenerates the report atomically only after every check passes; a
failed attempt leaves the prior report intact. The report stores command-output
digests rather than raw logs, contains no credential or model response content,
binds itself to the exact tested commit and all apparatus/protocol/scorer/
software digests, and independently reruns the documented command surface in a
fresh local clone. Raw trial artifacts remain ignored under
`artifacts/benchmark/`.

Adding the generated report creates a documentation-only commit after the
tested commit. The report's `benchmark_software_sha256`, protocol digest, scorer
digest, and lock digest must still match the repository. CI then repeats the
unpaid checks on the report-bearing commit.
