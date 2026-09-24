"""Agent Memory-native vector candidate retrieval.

This module deliberately owns only *candidate discovery*.  A vector similarity
score is retrieval evidence.  It is not currentness, truth, scope, permission,
lifecycle strength, or mutation authority.  Callers must send discovered
candidates through the existing governed recall-admission boundary before they
can influence active cognition.

The first profile uses a deterministic-rebuild posture instead of making
embeddings canonical memory.  Canonical facts remain authoritative; vector
representations are derived on demand from those facts through a versioned
representation provider.  This keeps restart/correction/deletion semantics
anchored to canonical state while the vector route is still young.

The route is intentionally representation-neutral.  EvolveAI and CodeGenome
provide implementation ancestry and behavioral evidence for vector retrieval,
but Agent Memory does not import, call, or require either runtime here.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Protocol, runtime_checkable

from ..state.substrate import Fact


SEMANTIC_VECTOR_ROUTE = "semantic_vector"
COSINE_SIMILARITY = "cosine"
DETERMINISTIC_REBUILD_POSTURE = "deterministic_rebuild_from_canonical"


@dataclass(frozen=True)
class VectorRepresentationSpec:
    """Versioned identity for a derived vector representation.

    ``config_digest`` binds configuration that can materially change vector
    values even when the implementation/version string is unchanged.  A
    production model-backed representation should bind model/runtime/config
    identity here rather than relying on a friendly model name.
    """

    representation_ref: str
    representation_version: str
    config_digest: str
    dimensions: int
    deterministic_rebuild: bool
    rebuild_posture: str = DETERMINISTIC_REBUILD_POSTURE
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if not self.representation_ref or not self.representation_version:
            raise ValueError("vector representation identity and version are required")
        if not self.config_digest:
            raise ValueError("vector representation config_digest is required")
        if self.dimensions < 1:
            raise ValueError("vector representation dimensions must be positive")
        if not self.deterministic_rebuild:
            raise ValueError(
                "the first native vector profile requires deterministic rebuild from canonical state"
            )
        if self.rebuild_posture != DETERMINISTIC_REBUILD_POSTURE:
            raise ValueError("unsupported vector rebuild posture")
        if self.authority_effect != "none":
            raise ValueError("vector representations cannot have authority effect")


class VectorRepresentationProvider(Protocol):
    """Representation contract used by the native vector route."""

    @property
    def spec(self) -> VectorRepresentationSpec: ...

    def embed(self, text: str) -> tuple[float, ...]: ...


@runtime_checkable
class AllFactsTemporalGraphPort(Protocol):
    """Optional canonical-state enumeration used for deterministic rebuild.

    This is intentionally not added to the required ``TemporalGraphPort``.
    Substrates that cannot enumerate canonical facts remain valid substrates;
    they simply cannot advertise the native vector route under this profile.
    """

    def all_facts(self) -> Iterable[Fact]: ...


@dataclass(frozen=True)
class VectorCandidateHit:
    candidate_ref: str
    similarity: float
    representation_ref: str
    representation_version: str
    representation_config_digest: str
    vector_dimension: int
    similarity_metric: str = COSINE_SIMILARITY
    rebuild_posture: str = DETERMINISTIC_REBUILD_POSTURE
    currentness_basis: str = "governed_recall_admission"
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if not math.isfinite(self.similarity):
            raise ValueError("vector similarity must be finite")
        if self.authority_effect != "none":
            raise ValueError("vector candidate hits cannot have authority effect")


class NativeVectorCandidateRetriever:
    """Bounded O(N) cosine candidate route over canonical Agent Memory facts.

    O(N) scan is deliberate for the first native slice.  It gives us a small,
    deterministic, inspectable correctness surface before introducing ANN
    indexes, background rebuild workers, or model-specific storage formats.
    Those optimizations can be layered in later without changing recall
    authority or canonical memory identity.
    """

    def __init__(
        self,
        representation: VectorRepresentationProvider,
        *,
        minimum_similarity: float = 0.0,
    ) -> None:
        self.representation = representation
        self.spec = representation.spec
        if not math.isfinite(minimum_similarity):
            raise ValueError("minimum_similarity must be finite")
        if minimum_similarity < -1.0 or minimum_similarity > 1.0:
            raise ValueError("minimum_similarity must be between -1 and 1")
        self.minimum_similarity = float(minimum_similarity)
        # Force validation even for duck-typed providers returning a subclass or
        # proxy object.  Accessing all fields here also makes missing metadata a
        # startup failure rather than a query-time ambiguity.
        VectorRepresentationSpec(
            representation_ref=self.spec.representation_ref,
            representation_version=self.spec.representation_version,
            config_digest=self.spec.config_digest,
            dimensions=self.spec.dimensions,
            deterministic_rebuild=self.spec.deterministic_rebuild,
            rebuild_posture=self.spec.rebuild_posture,
            authority_effect=self.spec.authority_effect,
        )

    def available_for(self, substrate: object) -> bool:
        return isinstance(substrate, AllFactsTemporalGraphPort)

    def search(
        self,
        substrate: AllFactsTemporalGraphPort,
        query: str,
        *,
        group_id: str,
        candidate_limit: int,
    ) -> list[VectorCandidateHit]:
        if candidate_limit < 0:
            raise ValueError("candidate_limit must be non-negative")
        if candidate_limit == 0:
            return []
        if not self.available_for(substrate):
            raise ValueError("substrate does not support canonical fact enumeration")

        query_vector = self._validated_vector(self.representation.embed(query))
        if self._norm(query_vector) == 0.0:
            return []

        hits: list[VectorCandidateHit] = []
        for fact in substrate.all_facts():
            if fact.group_id != group_id:
                continue
            candidate_vector = self._validated_vector(
                self.representation.embed(fact.fact_text)
            )
            similarity = self._cosine(query_vector, candidate_vector)
            if similarity <= self.minimum_similarity:
                continue
            hits.append(
                VectorCandidateHit(
                    candidate_ref=fact.uuid,
                    similarity=similarity,
                    representation_ref=self.spec.representation_ref,
                    representation_version=self.spec.representation_version,
                    representation_config_digest=self.spec.config_digest,
                    vector_dimension=self.spec.dimensions,
                    rebuild_posture=self.spec.rebuild_posture,
                )
            )

        hits.sort(key=lambda item: (-item.similarity, item.candidate_ref))
        return hits[:candidate_limit]

    def _validated_vector(self, value: tuple[float, ...]) -> tuple[float, ...]:
        try:
            vector = tuple(float(component) for component in value)
        except (TypeError, ValueError) as exc:
            raise ValueError("vector representation returned non-numeric values") from exc
        if len(vector) != self.spec.dimensions:
            raise ValueError(
                "vector representation dimension mismatch: "
                f"expected {self.spec.dimensions}, got {len(vector)}"
            )
        if any(not math.isfinite(component) for component in vector):
            raise ValueError("vector representation returned non-finite values")
        return vector

    @staticmethod
    def _norm(vector: tuple[float, ...]) -> float:
        return math.sqrt(sum(component * component for component in vector))

    @classmethod
    def _cosine(
        cls,
        left: tuple[float, ...],
        right: tuple[float, ...],
    ) -> float:
        left_norm = cls._norm(left)
        right_norm = cls._norm(right)
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        score = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
        # Floating-point roundoff can produce 1.0000000000000002.  Keep the
        # metric inside its mathematical domain without changing ordering.
        return max(-1.0, min(1.0, score))
