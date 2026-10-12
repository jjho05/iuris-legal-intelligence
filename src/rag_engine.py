"""
Motor Vectorial RAG Dinámico Multi-Corpus (rag_engine.py).
Permite alternar entre marcos legales (Corporativo, Laboral LFT) o indexar en caliente
documentos y contratos subidos por el usuario (PDF/Word convertidos a Markdown).
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import numpy as np
from src.config import settings, BASE_DIR


class VectorRAGEngine:
    """Motor de recuperación fáctica con soporte multi-corpus y documentos dinámicos."""

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self._embedder = None
        self.current_corpus_id = "corporativo"
        self.documentos: List[str] = []
        self.titulos: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.active_custom_doc: Optional[str] = None
        
        # Cargar corpus corporativo por defecto
        self.load_corpus("corporativo")

    @property
    def embedder(self):
        """Carga perezosa del modelo de embeddings."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"[AVISO RAG] Fallback a vectorizador local determinista: {e}")
                self._embedder = FallbackEmbedder()
        return self._embedder

    def load_corpus(self, corpus_id: str):
        """Carga un marco legal predefinido: 'corporativo' o 'lft' (Laboral)."""
        self.current_corpus_id = corpus_id
        self.active_custom_doc = None

        if corpus_id == "lft":
            path = BASE_DIR / "data" / "lft_reformas_clave.txt"
        else:
            path = settings.CORPUS_FILE_PATH

        if not path.exists():
            path = settings.CORPUS_FILE_PATH

        with open(path, "r", encoding="utf-8") as f:
            contenido = f.read()

        self._index_text(contenido, source_label=corpus_id.upper())

    def index_custom_markdown(self, filename: str, markdown_text: str):
        """Indexa en tiempo real un contrato o documento subido por el usuario (PDF/DOCX a MD)."""
        self.current_corpus_id = "custom"
        self.active_custom_doc = filename
        self._index_text(markdown_text, source_label=f"Documento: {filename}")
        print(f"[RAG] Indexado documento dinámico '{filename}' con {len(self.documentos)} secciones.")

    def _index_text(self, text: str, source_label: str):
        """Segmenta e indexa texto por artículos o encabezados."""
        # Dividir por "Artículo " o encabezados de Markdown "### " o "## "
        if "### " in text or "## " in text:
            raw_blocks = re.split(r"\n(?=#{2,3}\s+)", text)
        else:
            raw_blocks = [b.strip() for b in text.split("Artículo ") if b.strip()]

        self.documentos = []
        self.titulos = []

        for b in raw_blocks:
            b_str = b.strip()
            if not b_str or len(b_str) < 25:
                continue
            if b_str.startswith("ESTATUTO") or b_str.startswith("Versión") or b_str.startswith("LEY FEDERAL"):
                continue

            if not b_str.startswith("#") and not b_str.startswith("Artículo"):
                texto_seccion = "Artículo " + b_str
            else:
                texto_seccion = b_str

            first_line = texto_seccion.split("\n")[0].replace("#", "").strip()
            self.titulos.append(f"[{source_label}] {first_line[:75]}")
            self.documentos.append(texto_seccion)

        if not self.documentos:
            # Respaldo por párrafos dobles
            self.documentos = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 35]
            self.titulos = [f"[{source_label}] Sección {i+1}" for i in range(len(self.documentos))]

        self.embeddings = self.embedder.encode(
            self.documentos,
            normalize_embeddings=True,
            show_progress_bar=False
        )

    def search(self, pregunta: str, top_k: Optional[int] = None, umbral: Optional[float] = None) -> List[Dict[str, Any]]:
        """Calcula similitud coseno y filtra por umbral de veracidad fáctica."""
        top_k = top_k or settings.RAG_TOP_K
        umbral = umbral or settings.RAG_SIMILARITY_THRESHOLD

        if self.embeddings is None or len(self.documentos) == 0:
            return []

        q_emb = self.embedder.encode([pregunta], normalize_embeddings=True)[0]
        similitudes = np.dot(self.embeddings, q_emb)
        mejores_indices = np.argsort(similitudes)[::-1][:top_k]

        resultados = []
        for idx in mejores_indices:
            puntaje = float(similitudes[idx])
            if puntaje >= umbral:
                resultados.append({
                    "titulo": self.titulos[idx],
                    "texto": self.documentos[idx],
                    "confianza": round(puntaje, 4),
                    "indice": int(idx),
                    "corpus": self.current_corpus_id
                })
        return resultados


class FallbackEmbedder:
    """Embebedor determinista para entornos ligeros."""

    def __init__(self, dim=384):
        self.dim = dim

    def encode(self, texts: List[str], normalize_embeddings: bool = True, show_progress_bar: bool = False) -> np.ndarray:
        vectors = []
        for t in texts:
            words = t.lower().split()
            vec = np.zeros(self.dim, dtype=np.float32)
            for w in words:
                idx = hash(w) % self.dim
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if normalize_embeddings and norm > 0:
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors)
