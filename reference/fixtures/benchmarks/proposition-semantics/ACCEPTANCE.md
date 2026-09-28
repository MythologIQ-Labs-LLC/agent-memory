# Proposition-semantics accepted-gold status

Current status: **accepted and scored** for #594.

This file is the current-state companion to the historical draft/provenance README. The v1-v5 draft files remain unchanged and keep their draft labels; they are provenance, not the accepted file.

Accepted gold is `gold-v1.json`, an acceptance manifest over byte-frozen `draft-annotations-v5.json`.

- accepted by: `Knapp-Kevin`
- accepted at: `2026-09-28T14:02:38Z`
- PR review: `5339771805`
- source head: `6210ab5789de9246f9893a3f82cc44fb410e0ce8`
- v5 source sha256: `bb336e72281b64dbdd090447194a67f0638b820a4adb18f1463d24c77859aec7`
- rubric v5 sha256: `94775c3c6b4f4bcc13f8b3455e7cfda7a90c8dfa54dade0937f89270ca1618ad`
- sample sha256: `b1957ca4ff95c3b8a227b8b75f74327911172305cf770c927d56091e7fedd8d3`
- text-hash-list sha256: `3dceb7cde08abf45af3ea1d4dc12d117c390a3441eed38b3ca2273e04f986b88`
- accepted counts: 148 known / 35 ambiguous / 85 unknown.

`load_gold` accepts the manifest only after verifying the v5 digest and item count. Direct loading of draft v1-v5 remains refused.

`property-aliases-gold-v1.json` was frozen with zero aliases before the interpreter score. It must never be populated after seeing score failures merely to improve the result.

First score:
- head `73216bebc596de4876692a8f00d1e3fabaa899f1`
- workflow run `36434626348`
- artifact `10974877443`
- artifact sha256 `34decf958f7ed1b537241b360cc863eb8904ca27aa220fcf48c876b4975345f9`
- deterministic replay identical.

Part R headline: known precision 0.800, known recall 0.148; unknown precision 1.000, unknown recall 0.848. See the #594 closeout and `phase-b-score-v1.json` for the bounded interpretation and failure classes.
