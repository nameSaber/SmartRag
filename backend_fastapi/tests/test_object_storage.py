class _FakeObject:
    def __init__(self, content: bytes):
        self._content = content

    def read(self):
        return self._content

    def close(self):
        return None

    def release_conn(self):
        return None


class _FakeMinio:
    def __init__(self):
        self.buckets = set()
        self.objects = {}

    def bucket_exists(self, bucket):
        return bucket in self.buckets

    def make_bucket(self, bucket):
        self.buckets.add(bucket)

    def put_object(self, bucket, key, data, length, content_type):
        assert length >= 0
        assert content_type
        self.objects[(bucket, key)] = data.read()

    def get_object(self, bucket, key):
        return _FakeObject(self.objects[(bucket, key)])


def test_minio_object_storage_put_and_get_bytes():
    from app.integrations.object_storage import MinioObjectStorage, chunk_key, document_key

    fake = _FakeMinio()
    storage = MinioObjectStorage(client=fake, bucket="test-bucket")

    ref = storage.put_bytes(chunk_key("abc", 0), b"hello", "text/plain")
    content = storage.get_bytes(ref.key)

    assert ref.bucket == "test-bucket"
    assert content == b"hello"
    assert document_key("abc", "demo.txt") == "documents/abc/demo.txt"
