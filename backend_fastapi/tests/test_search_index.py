class _FakeIndices:
    def __init__(self):
        self.created = False
        self.refreshed = False

    def exists(self, index):
        return self.created

    def create(self, index, mappings):
        self.created = True
        self.mappings = mappings

    def refresh(self, index):
        self.refreshed = True


class _FakeElasticsearch:
    def __init__(self):
        self.indices = _FakeIndices()
        self.indexed = []
        self.last_query = None

    def index(self, index, id, document):
        self.indexed.append((index, id, document))

    def search(self, index, size, query):
        self.last_query = query
        return {"hits": {"hits": [{"_score": 2.5, "_source": {"fileMd5": "abc", "chunkId": 0, "textContent": "hello"}}]}}


def test_elasticsearch_index_indexes_and_searches():
    from app.integrations.search_index import ElasticsearchIndex

    fake = _FakeElasticsearch()
    index = ElasticsearchIndex(client=fake, index_name="docs")
    index.index_chunks([{"fileMd5": "abc", "chunkId": 0, "textContent": "hello"}])
    results = index.search("hello", user_id=1, org_tags=["default"], top_k=3, query_vector=[0.1] * 8)

    assert fake.indices.created is True
    assert fake.indices.refreshed is True
    assert fake.indexed[0][1] == "abc:0"
    assert results[0]["retrievalMode"] == "hybrid"
    assert fake.last_query["script_score"]["query"]["bool"]["must"][0]["match"]["textContent"] == "hello"
    assert fake.last_query["script_score"]["script"]["params"]["query_vector"] == [0.1] * 8
