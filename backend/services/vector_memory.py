import os
import time
import tempfile
import traceback
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from config import settings
from database import SessionLocal
import models

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None

# optional integration with an external MemoryModule providing `recall` API
try:
    try:
        from memory_module import MemoryModule
    except Exception:
        try:
            from .memory_module import MemoryModule
        except Exception:
            MemoryModule = None
except Exception:
    MemoryModule = None

VECTOR_DIM = 128
DEFAULT_COLLECTION_NAME = "visiontrader_memory"


def _normalize_text(value: str) -> str:
    return re.sub(r"[^\w\s]", " ", (value or "").lower()).strip()


def _text_embedding(text: str) -> List[float]:
    tokens = re.findall(r"\w+", _normalize_text(text))
    if not tokens:
        return [0.0] * VECTOR_DIM

    vector = [0.0] * VECTOR_DIM
    for token in tokens:
        idx = abs(hash(token)) % VECTOR_DIM
        vector[idx] += 1.0

    length = sum(x * x for x in vector) ** 0.5
    if length > 0:
        vector = [x / length for x in vector]
    return vector


def _text_similarity(a: str, b: str) -> float:
    a_tokens = set(re.findall(r"\w+", _normalize_text(a)))
    b_tokens = set(re.findall(r"\w+", _normalize_text(b)))
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return len(intersection) / max(len(union), 1)


class VectorMemoryService:
    def __init__(self):
        self.use_chroma = False
        self.client = None
        self.collection = None
        self.memory_cache: List[Dict[str, Any]] = []
        self._init_storage()
        # link to external MemoryModule.recall if available
        self.memory_module_recall = None
        try:
            if MemoryModule is not None and hasattr(MemoryModule, 'recall'):
                # recall may be a static function or bound method
                self.memory_module_recall = getattr(MemoryModule, 'recall')
        except Exception:
            self.memory_module_recall = None

    def _init_storage(self):
        if chromadb is None or Settings is None:
            print("Vector memory disabled: chromadb package not installed.")
            return

        persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY") or os.path.join(os.getcwd(), ".chromadb")
        try:
            os.makedirs(persist_dir, exist_ok=True)
        except Exception:
            persist_dir = os.path.join(tempfile.gettempdir(), "visiontrader_chromadb")
            try:
                os.makedirs(persist_dir, exist_ok=True)
            except Exception as exc:
                print("Vector memory disabled: unable to create persistence directory:", exc)
                return

        try:
            try:
                settings = Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir, anonymized_telemetry=False)
            except TypeError:
                settings = Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir)
            self.client = chromadb.Client(settings)
            try:
                self.collection = self.client.get_collection(name=DEFAULT_COLLECTION_NAME)
            except Exception:
                self.collection = self.client.create_collection(name=DEFAULT_COLLECTION_NAME)
            self.use_chroma = True
            print(f"Vector memory initialized with ChromaDB at {persist_dir}.")
        except Exception as exc:
            print("Failed to initialize ChromaDB vector memory:", exc)
            traceback.print_exc()
            self.use_chroma = False
            self.client = None
            self.collection = None

    def store_analysis(self, analysis_id: int, visual_description: str, result: str, db: Optional[SessionLocal] = None) -> bool:
        if not visual_description:
            return False

        metadata = {
            "analysis_id": str(analysis_id),
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.use_chroma and self.collection is not None:
            try:
                self.collection.add(
                    ids=[str(analysis_id)],
                    documents=[visual_description],
                    metadatas=[metadata],
                    embeddings=[_text_embedding(visual_description)]
                )
                return True
            except Exception as exc:
                print("Failed to store vector entry, switching to fallback:", exc)
                traceback.print_exc()
                self.use_chroma = False

        existing = next((entry for entry in self.memory_cache if entry["analysis_id"] == str(analysis_id)), None)
        if existing:
            existing.update({"visual_description": visual_description, "result": result, "created_at": datetime.now(timezone.utc)})
        else:
            self.memory_cache.append({
                "analysis_id": str(analysis_id),
                "visual_description": visual_description,
                "result": result,
                "created_at": datetime.now(timezone.utc)
            })
        return True

    def find_similar(self, visual_description: str, top_k: int = 3, db: Optional[SessionLocal] = None) -> List[Dict[str, Any]]:
        if not visual_description:
            return []
        # first try high-quality recall from MemoryModule if available
        if self.memory_module_recall:
            try:
                recall_results = self.memory_module_recall(visual_description, top_k=top_k)
                if recall_results:
                    matches = []
                    for item in recall_results[:top_k]:
                        matches.append({
                            "analysis_id": str(item.get("analysis_id") or item.get("id")),
                            "market": item.get("market"),
                            "result": item.get("result"),
                            "created_at": item.get("created_at"),
                            "score": float(item.get("score") or 0.0),
                            "description": item.get("description") or item.get("visual_description")
                        })
                    return matches
            except Exception:
                # fall back to built-in stores on any failure
                traceback.print_exc()

        if self.use_chroma and self.collection is not None:
            try:
                query_results = self.collection.query(
                    query_embeddings=[_text_embedding(visual_description)],
                    n_results=top_k,
                    include=["metadatas", "distances", "documents"]
                )
                matches = []
                if query_results and len(query_results.get("ids", [])) > 0:
                    for idx, rid in enumerate(query_results["ids"][0]):
                        matches.append({
                            "analysis_id": rid,
                            "market": query_results["metadatas"][0][idx].get("market"),
                            "result": query_results["metadatas"][0][idx].get("result"),
                            "created_at": query_results["metadatas"][0][idx].get("created_at"),
                            "score": float(query_results["distances"][0][idx]) if query_results.get("distances") else None,
                            "description": query_results["documents"][0][idx]
                        })
                return matches
            except Exception as exc:
                print("ChromaDB similarity query failed:", exc)
                traceback.print_exc()
                self.use_chroma = False

        candidates = []
        if db is not None:
            try:
                rows = db.query(models.Analysis).filter(models.Analysis.description.isnot(None)).all()
                for row in rows:
                    candidates.append({
                        "analysis_id": str(row.id),
                        "market": row.market,
                        "result": None,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "description": row.description,
                        "score": _text_similarity(visual_description, row.description)
                    })
            except Exception as exc:
                print("Fallback text search read from DB failed:", exc)
                traceback.print_exc()
        else:
            for row in self.memory_cache:
                candidates.append({
                    "analysis_id": row["analysis_id"],
                    "market": row.get("market"),
                    "result": row.get("result"),
                    "created_at": row.get("created_at").isoformat() if isinstance(row.get("created_at"), datetime) else row.get("created_at"),
                    "description": row.get("visual_description"),
                    "score": _text_similarity(visual_description, row.get("visual_description", ""))
                })

        candidates = [c for c in candidates if c.get("score", 0) > 0]
        candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
        return candidates[:top_k]

    def get_insight(self, visual_description: str, top_k: int = 3, db: Optional[SessionLocal] = None) -> str:
        similar = self.find_similar(visual_description, top_k=top_k, db=db)
        if not similar:
            return "لا يوجد شارتات سابقة كافية للتشابه. تابع التحليل مع تحديث النتائج لاحقاً."

        top = similar[0]
        result_label = top.get("result") or "غير معروف"
        insight = f"هذا الشارت يشبه صفقة سابقة بتاريخ {top.get('created_at', 'غير معروف')} على زوج {top.get('market', 'غير محدد')}، وكانت النتيجة {result_label}."

        loss_count = sum(1 for item in similar if str(item.get("result", "")).lower() in ("loss", "خسارة", "خاسر"))
        if loss_count >= 2:
            insight += " تحذير: نمط مشابه فشل مرتين من قبل ⚠️"
        elif result_label.lower() in ("win", "ربح", "رابح"):
            insight += " ✅ النمط المطلوب يبدو مدعومًا بنتائج إيجابية سابقة."

        return insight

    def delete_old(self, days: int = 90, db: Optional[SessionLocal] = None) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = 0

        if self.use_chroma and self.collection is not None:
            try:
                all_items = self.collection.get(include=["metadatas", "ids"])
                delete_ids = []
                for idx, metadata in enumerate(all_items.get("metadatas", [])[0] if all_items.get("metadatas") else []):
                    created = metadata.get("created_at")
                    if created:
                        try:
                            created_dt = datetime.fromisoformat(created)
                            if created_dt < cutoff:
                                delete_ids.append(all_items["ids"][0][idx])
                        except Exception:
                            continue
                if delete_ids:
                    self.collection.delete(ids=delete_ids)
                    deleted = len(delete_ids)
            except Exception as exc:
                print("Delete-old in ChromaDB failed:", exc)
                traceback.print_exc()

        before_count = len(self.memory_cache)
        self.memory_cache = [item for item in self.memory_cache if not isinstance(item.get("created_at"), datetime) or item["created_at"] >= cutoff]
        deleted += before_count - len(self.memory_cache)

        return deleted


vector_memory = VectorMemoryService()
