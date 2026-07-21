import re
from typing import List


class ChunkingService:
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 400, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks.
        """
        chunks = []
        sentences = re.split(r'(?<=[.!?\n])\s+', text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                keep_count = max(1, len(current_chunk) // 3)
                current_chunk = current_chunk[-keep_count:]
                current_length = sum(len(s) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
