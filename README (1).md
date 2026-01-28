# 🚀 PyQuickCache

**PyQuickCache** is a production‑grade, thread‑safe, in‑memory caching
library for Python featuring TTL expiration, pluggable eviction
policies, persistence, metrics, and extensibility via clean
registry‑based architecture.

It is designed for backend systems, APIs, and high‑performance
applications that require fast local caching with predictable behavior.

------------------------------------------------------------------------

## ✨ Features

-   ⚡ Fast in‑memory key‑value store
-   ⏱ Per‑key and default TTL (time‑to‑live)
-   🧠 Eviction policies:
    -   LRU (Least Recently Used)
    -   LFU (Least Frequently Used + LRU tie‑break)
    -   FIFO (First In First Out)
-   🔄 Pluggable serializers:
    -   JSON
    -   Pickle
-   💾 Disk persistence for cache + metrics
-   📊 Optional metrics collection
-   🧵 Fully thread‑safe
-   🧩 Extensible via registries (custom eviction & serializers)
-   🧹 Background cleanup thread for expired entries
-   ❌ Pythonic exception‑based API

------------------------------------------------------------------------

## 📦 Installation

From PyPI:

``` bash
pip install pyquickcache
```

Local development:

``` bash
pip install -e .
```

------------------------------------------------------------------------

## 🏗 Core Concepts

-   `QuickCache` → Main cache class
-   `QuickCacheConfig` → Configuration object
-   Eviction policies & serializers are loaded dynamically via registry
    decorators

------------------------------------------------------------------------

## 🚀 Quick Start

``` python
from pyquickcache import QuickCache, QuickCacheConfig

config = QuickCacheConfig(
    max_size=1000,
    default_ttl=60,
    eviction_policy="lru",
    serializer="json"
)

cache = QuickCache(config)

cache.set("user_id", 42)
print(cache.get("user_id"))
```

------------------------------------------------------------------------

## ⚙️ Configuration with QuickCacheConfig

``` python
from pyquickcache import QuickCacheConfig

config = QuickCacheConfig(
    max_size=500,
    default_ttl=120,
    eviction_policy="lfu",      # lru | lfu | fifo
    serializer="pickle",       # json | pickle
    enable_metrics=True,
    cleanup_interval=10,
    storage_dir="cache_data",
    filename="cache",
)
```

Then:

``` python
cache = QuickCache(config)
```

------------------------------------------------------------------------

## 🧠 Eviction Policies

  Name     Description
  -------- ---------------------------------------
  `lru`    Least recently accessed
  `lfu`    Least frequently used (LRU tie‑break)
  `fifo`   Oldest inserted first

Usage:

``` python
QuickCacheConfig(eviction_policy="fifo")
```

------------------------------------------------------------------------

## 🔄 Serializers

  Name       Description
  ---------- -----------------------------------------
  `json`     Human‑readable
  `pickle`   Binary (fast, supports complex objects)

Usage:

``` python
QuickCacheConfig(serializer="pickle")
```

------------------------------------------------------------------------

## 🧪 Public API

### Core operations

``` python
get(key)
set(key, value, ttl_sec=None)
add(key, value, ttl_sec=None)
update(key, value, ttl_sec=None)
delete(key)
```

### Bulk operations

``` python
set_many(dict, ttl_sec=None)
get_many(list_of_keys)
delete_many(list_of_keys)
```

### Cache info

``` python
size()
valid_size()
clear()
cleanup()
```

### Persistence

``` python
save_to_disk(filepath=None, use_timestamp=False)
load_from_disk(filepath=None)
```

### Metrics

``` python
get_metrics_snapshot()
reset_metrics()
save_metrics_to_disk(filepath=None, use_timestamp=False)
```

### Lifecycle

``` python
stop()
```

------------------------------------------------------------------------

## ⏱ TTL Example

``` python
cache.set("token", "abc", ttl_sec=5)

# After 5 seconds
cache.get("token")  # raises KeyExpired
```

------------------------------------------------------------------------

## 💾 Disk Persistence Example

``` python
cache.save_to_disk("my_cache_file")

cache.clear()

cache.load_from_disk("my_cache_file")
```

------------------------------------------------------------------------

## 📊 Metrics Example

``` python
snapshot = cache.get_metrics_snapshot()
print(snapshot)

cache.save_metrics_to_disk("metrics")
```

------------------------------------------------------------------------

## 🛠 Creating a Custom Eviction Policy

``` python
from pyquickcache.eviction_policy import BaseEvictionPolicy
from pyquickcache.registry.decorators import register_eviction_policy

@register_eviction_policy("my_policy")
class MyPolicy(BaseEvictionPolicy):

    def on_add(self, cache, key): pass
    def on_update(self, cache, key): pass
    def on_access(self, cache, key): pass
    def on_delete(self, cache, key): pass

    def select_eviction_key(self, cache):
        return next(iter(cache))
```

Use it:

``` python
QuickCacheConfig(eviction_policy="my_policy")
```

------------------------------------------------------------------------

## 🧬 Creating a Custom Serializer

``` python
from pyquickcache.serializer import BaseSerializer
from pyquickcache.registry.decorators import register_serializer

@register_serializer("my_serializer")
class MySerializer(BaseSerializer):

    extension = "txt"
    is_binary = False

    def serialize(self, data):
        return str(data)

    def deserialize(self, data):
        return eval(data)
```

Use it:

``` python
QuickCacheConfig(serializer="my_serializer")
```

------------------------------------------------------------------------

## 🏛 Architecture Overview

    QuickCache
     ├── OrderedDict storage
     ├── EvictionPolicy (strategy)
     ├── Serializer
     ├── FileManager (persistence)
     ├── Metrics system
     ├── Background cleanup thread
     └── Registry system

------------------------------------------------------------------------

## 🔒 Thread Safety

All public APIs are protected via re‑entrant locks (`RLock`) and are
safe for:

-   Web servers
-   Background workers
-   Multi‑threaded services

------------------------------------------------------------------------

## 🛣 Roadmap

-   Async API
-   Redis protocol adapter
-   Distributed cache mode
-   Django integration
-   Prometheus metrics exporter

------------------------------------------------------------------------

## 👨‍💻 Author

Naman Malik

------------------------------------------------------------------------

## 📄 License

MIT License
