from elasticsearch import Elasticsearch

from app.core.config import settings


class ElasticsearchIndex:
    def __init__(self, client: Elasticsearch | None = None, index_name: str | None = None):
        self.client = client or Elasticsearch(settings.es_url)
        self.index_name = index_name or settings.es_index_name

    def ensure_index(self) -> None:
        # 当前先使用文本检索字段；后续接入 embedding 后补充 dense_vector 映射。
        if self.client.indices.exists(index=self.index_name):
            return
        self.client.indices.create(
            index=self.index_name,
            mappings={
                "properties": {
                    "fileMd5": {"type": "keyword"},
                    "chunkId": {"type": "integer"},
                    "textContent": {"type": "text", "analyzer": "standard"},
                    "pageNumber": {"type": "integer"},
                    "anchorText": {"type": "text"},
                    "fileName": {"type": "keyword"},
                    "userId": {"type": "integer"},
                    "orgTag": {"type": "keyword"},
                    "isPublic": {"type": "boolean"},
                }
            },
        )

    def index_chunks(self, chunks: list[dict]) -> None:
        self.ensure_index()
        for chunk in chunks:
            doc_id = f"{chunk['fileMd5']}:{chunk['chunkId']}"
            self.client.index(index=self.index_name, id=doc_id, document=chunk)
        self.client.indices.refresh(index=self.index_name)

    def search(self, query: str, user_id: int, org_tags: list[str], top_k: int) -> list[dict]:
        filters = [
            {
                "bool": {
                    "should": [
                        {"term": {"userId": user_id}},
                        {"term": {"isPublic": True}},
                        {"terms": {"orgTag": org_tags or ["__none__"]}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        ]
        response = self.client.search(
            index=self.index_name,
            size=top_k,
            query={"bool": {"must": [{"match": {"textContent": query}}], "filter": filters}},
        )
        results = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            source["score"] = hit.get("_score", 0)
            source["retrievalMode"] = "elasticsearch"
            source["matchedChunkText"] = source.get("textContent", "")
            results.append(source)
        return results


def get_search_index() -> ElasticsearchIndex:
    return ElasticsearchIndex()
