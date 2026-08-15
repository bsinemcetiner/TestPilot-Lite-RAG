import re
from typing import List


class ChunkingService:
    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 400,
        overlap: int = 100
    ) -> List[str]:
        """
        Split text into chunks.

        If the document contains numbered requirements such as:
        1. Requirement...
        2. Requirement...
        each requirement is stored as a separate chunk.

        Otherwise, fall back to normal text chunking.
        """

        text = text.strip()

        if not text:
            return []

        # Detect numbered requirements.
        # Example:
        # 1. A registered user...
        # 2. The system must...
        requirement_pattern = re.compile(
            r"(?ms)^\s*(\d+)\.\s+(.*?)(?=^\s*\d+\.\s+|\Z)"
        )

        matches = requirement_pattern.findall(text)

        if matches:
            chunks = []

            # Preserve feature/header information if available.
            first_requirement_match = re.search(
                r"(?m)^\s*1\.\s+",
                text
            )

            header = ""
            if first_requirement_match:
                header = text[:first_requirement_match.start()].strip()

            for index, (_, requirement_text) in enumerate(matches):
                requirement_text = requirement_text.strip()

                if not requirement_text:
                    continue

                # Keep document header with the first requirement
                # so retrieval still knows which feature it belongs to.
                if index == 0 and header:
                    chunk = f"{header}\n\n{requirement_text}"
                else:
                    chunk = requirement_text

                chunks.append(chunk)

            return chunks

        # ---------------------------------------------------------
        # Fallback for normal unstructured documents
        # ---------------------------------------------------------

        sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            text
        )

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            sentence_length = len(sentence)

            if (
                current_chunk
                and current_length + sentence_length + 1 > chunk_size
            ):
                chunk_text = " ".join(current_chunk).strip()
                chunks.append(chunk_text)

                # Character-based overlap from the end of previous chunk.
                if overlap > 0:
                    overlap_text = chunk_text[-overlap:].strip()

                    current_chunk = (
                        [overlap_text]
                        if overlap_text
                        else []
                    )

                    current_length = len(overlap_text)
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(sentence)
            current_length += sentence_length + 1

        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()

            if chunk_text:
                chunks.append(chunk_text)

        return chunks