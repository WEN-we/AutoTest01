"""统一密钥源（security.py）单元测试：三级优先级 + 缓存 + 只读兜底。"""
import pytest

from quality_platform import security


@pytest.fixture(autouse=True)
def reset_cache(monkeypatch):
    """每个用例重置模块级缓存（否则首例结果会串到后续用例）。"""
    monkeypatch.setattr(security, "_cached", None)
    yield
    monkeypatch.setattr(security, "_cached", None)


class TestEnvPriority:
    def test_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("PLATFORM_SECRET", "env-secret-abc")
        assert security.get_platform_secret() == "env-secret-abc"

    def test_env_var_trimmed(self, monkeypatch):
        monkeypatch.setenv("PLATFORM_SECRET", "  spaced  ")
        assert security.get_platform_secret() == "spaced"

    def test_blank_env_falls_through(self, monkeypatch, tmp_path):
        """空/空白环境变量不生效，走文件分支。"""
        monkeypatch.setenv("PLATFORM_SECRET", "   ")
        monkeypatch.setattr(security, "_SECRET_FILE", tmp_path / "secret.key")
        val = security.get_platform_secret()
        assert val and val != ""

    def test_cache_returns_same_value(self, monkeypatch):
        monkeypatch.setenv("PLATFORM_SECRET", "cached-secret")
        first = security.get_platform_secret()
        monkeypatch.setenv("PLATFORM_SECRET", "changed-secret")
        assert security.get_platform_secret() == first     # 缓存生效


class TestSecretFile:
    def test_generates_and_persists(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PLATFORM_SECRET", raising=False)
        secret_file = tmp_path / "data" / "secret.key"
        monkeypatch.setattr(security, "_SECRET_FILE", secret_file)
        val = security.get_platform_secret()
        assert len(val) == 64 and secret_file.exists()
        assert secret_file.read_text(encoding="utf-8").strip() == val

    def test_reads_existing_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PLATFORM_SECRET", raising=False)
        secret_file = tmp_path / "secret.key"
        secret_file.write_text("persisted-secret-value", encoding="utf-8")
        monkeypatch.setattr(security, "_SECRET_FILE", secret_file)
        assert security.get_platform_secret() == "persisted-secret-value"

    def test_persisted_survives_cache_reset(self, monkeypatch, tmp_path):
        """同一密钥文件重复读取（重启场景）返回同值 -> 密文/令牌跨重启可用。"""
        monkeypatch.delenv("PLATFORM_SECRET", raising=False)
        secret_file = tmp_path / "secret.key"
        monkeypatch.setattr(security, "_SECRET_FILE", secret_file)
        first = security.get_platform_secret()
        monkeypatch.setattr(security, "_cached", None)      # 模拟重启
        assert security.get_platform_secret() == first

    def test_unwritable_dir_falls_back_to_random(self, monkeypatch, tmp_path):
        """目录不可写 -> 进程内随机密钥兜底（不抛异常）。"""
        monkeypatch.delenv("PLATFORM_SECRET", raising=False)
        monkeypatch.setattr(security, "_SECRET_FILE",
                            tmp_path / "no_such" / "deep" / "secret.key")
        monkeypatch.setattr(security.Path, "mkdir",
                            lambda *a, **k: (_ for _ in ()).throw(PermissionError("read-only")))
        val = security.get_platform_secret()
        assert len(val) == 64        # token_hex(32) -> 64 字符
        assert security._cached == val
