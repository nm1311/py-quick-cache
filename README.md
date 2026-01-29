# 🚀 PyQuickCache

**PyQuickCache** is a production‑grade, thread‑safe, in‑memory caching
library for Python featuring TTL expiration, pluggable eviction
policies, persistence, metrics, and extensibility via a clean
registry‑based architecture.

It is designed for backend systems, APIs, and high‑performance
applications that require fast local caching with predictable behavior.

---

## ✨ Features

- ⚡ Fast in‑memory key‑value store
- ⏱ Per‑key and default TTL (time‑to‑live)
- 🧠 Eviction policies:
  - LRU (Least Recently Used)
  - LFU (Least Frequently Used + LRU tie‑break)
  - FIFO (First In First Out)
- 🔄 Pluggable serializers:
  - JSON
  - Pickle
- 💾 Disk persistence for cache + metrics
- 📊 Optional metrics collection
- 🧵 Fully thread‑safe
- 🧩 Extensible via registries (custom eviction & serializers)
- 🧹 Background cleanup thread for expired entries
- ✅ Pythonic exception‑based API

---

## 📦 Installation

```bash
pip install pyquickcache
```

Local development:

``` bash
pip install -e .
```


---

## 🚀 Quick Start

```python
from pyquickcache import QuickCache, QuickCacheConfig

config = QuickCacheConfig(
    max_size=1000,
    default_ttl=60,
    eviction_policy="lru",
    serializer="json",
)

cache = QuickCache(config)

# Initialize with default configuration
# cache = QuickCache()

cache.set("user_id", 42)
print(cache.get("user_id"))
```

---

## ⚙️ Configuration (`QuickCacheConfig`)

| Field | Description |
|-----|------------|
| `max_size` | Maximum number of entries |
| `default_ttl` | Default TTL in seconds |
| `cleanup_interval` | Background cleanup interval |
| `eviction_policy` | `lru`, `lfu`, `fifo` |
| `serializer` | `json`, `pickle` |
| `storage_dir` | Directory for persistence |
| `filename` | Base filename |
| `cache_timestamps` | Enable timestamps in filename 
| `enable_metrics` | Enable metrics collection |
| `metrics_serializer` | default `json` |
| `metrics_storage_dir` | Directory for cache metrics storage |
| `metrics_filename` | Metrics filename |
| `cache_metrics_timestamps` | Enable timestamps in metrics filename |
---

## 🧪 Public API Reference

### Core Operations

| Method | Description | Raises |
|------|------------|-------|
| `get(key)` | Retrieve value | `KeyNotFound`, `KeyExpired` |
| `set(key, value, ttl_sec=None)` | Insert or overwrite | `InvalidTTL` |
| `add(key, value, ttl_sec=None)` | Insert only if missing | `KeyAlreadyExists` |
| `update(key, value, ttl_sec=None)` | Update existing | `KeyNotFound` |
| `delete(key)` | Delete key | `KeyNotFound` |

---

### Bulk Operations

| Method | Description |
|------|------------|
| `set_many(data, ttl_sec=None)` | Insert many keys |
| `get_many(keys)` | Fetch many keys |
| `delete_many(keys)` | Delete many keys |

---

### Cache State

| Method | Description |
|------|------------|
| `size()` | Total keys |
| `valid_size()` | Non‑expired keys |
| `clear()` | Clear cache |
| `cleanup()` | Remove expired keys |

---

### Persistence

| Method | Description |
|------|------------|
| `save_to_disk(filepath=None, use_timestamp=False)` | Save cache |
| `load_from_disk(filepath=None)` | Load cache |

---

### Metrics

| Method | Description |
|------|------------|
| `get_metrics_snapshot()` | Return metrics dict |
| `reset_metrics()` | Reset metrics |
| `save_metrics_to_disk(filepath=None)` | Save metrics |

---

### Lifecycle

| Method | Description |
|------|------------|
| `stop()` | Stop background threads |

---

## 🧠 Built‑in Eviction Policies

| Name | Description |
|----|------------|
| `lru` | Least recently used |
| `lfu` | Least frequently used |
| `fifo` | First in first out |

---

## 🔄 Built‑in Serializers

| Name | Description |
|----|------------|
| `json` | Human‑readable |
| `pickle` | Binary, supports complex objects |

---

## 🛠 Custom Eviction Policy

```python
from pyquickcache import QuickCache, QuickCacheConfig

from pyquickcache.eviction_policy import BaseEvictionPolicy
from pyquickcache.decorators import register_eviction_policy

@register_eviction_policy("my_policy")
class MyPolicy(BaseEvictionPolicy):
    def on_add(self, cache, key): pass
    def on_update(self, cache, key): pass
    def on_access(self, cache, key): pass
    def on_delete(self, cache, key): pass

    def select_eviction_key(self, cache):
        return next(iter(cache))


config = QuickCacheConfig(eviction_policy="my_policy")
cache = QuickCache(config=config)

```

---

## 🧬 Custom Serializer

```python
from pyquickcache import QuickCache, QuickCacheConfig

from pyquickcache.serializer import BaseSerializer
from pyquickcache.decorators import register_serializer

@register_serializer("my_serializer")
class MySerializer(BaseSerializer):
    extension = "txt"
    is_binary = False

    def serialize(self, data):
        return str(data)

    def deserialize(self, data):
        return eval(data)

config = QuickCacheConfig(serializer="my_serializer")
cache = QuickCache(config=config)

```

---

## 🔒 Thread Safety

All public APIs are protected using `RLock` and are safe for
multi‑threaded environments.

---


## 👨‍💻 Author

Naman Malik

---

## 📄 License

MIT License

