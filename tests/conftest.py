import pytest
from lwapi.client import LwApiClient

@pytest.fixture
def client():
    # 指向本地测试服务或 mock 服务
    return LwApiClient(base_url="http://127.0.0.1:9999/api", wxid="wxid_test")
