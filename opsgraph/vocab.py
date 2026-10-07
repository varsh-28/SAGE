"""Controlled vocabulary and domain constants for the synthetic OpsGraph dataset."""

# key -> metadata. "phrases" are the natural-language variants used in incident text.
SYMPTOMS = {
    "high_latency": {
        "label": "High latency", "group": "Performance", "alert": "HighLatencyAlert",
        "alt": ["slow responses", "response time degradation"],
        "phrases": [
            "response times climbed well above the normal baseline",
            "requests became very slow",
            "p95 latency spiked",
            "users complained about sluggish pages",
        ],
    },
    "connection_errors": {
        "label": "Connection errors", "group": "Reliability", "alert": "ConnectionErrorAlert",
        "alt": ["connection refused", "connection resets"],
        "phrases": [
            "clients saw connection resets",
            "connection refused errors appeared in the logs",
            "intermittent failures when opening connections",
            "upstream calls failed to connect",
        ],
    },
    "timeouts": {
        "label": "Request timeouts", "group": "Performance", "alert": "TimeoutAlert",
        "alt": ["deadline exceeded", "gateway timeout"],
        "phrases": [
            "calls started timing out",
            "gateway timeouts were reported",
            "deadline exceeded errors increased",
            "requests hung until the client gave up",
        ],
    },
    "high_cpu": {
        "label": "High CPU usage", "group": "Resources", "alert": "HighCpuAlert",
        "alt": ["cpu spike", "processor saturation"],
        "phrases": [
            "CPU usage pinned near the ceiling",
            "a CPU spike was visible on the dashboards",
            "nodes ran hot on compute",
            "load average climbed sharply",
        ],
    },
    "stale_data": {
        "label": "Stale data", "group": "Data", "alert": "DataFreshnessAlert",
        "alt": ["outdated records", "out-of-date reads"],
        "phrases": [
            "users saw outdated records",
            "reads returned old values",
            "recent updates were missing from responses",
            "data freshness checks failed",
        ],
    },
    "error_rate": {
        "label": "Elevated error rate", "group": "Reliability", "alert": "ErrorRateAlert",
        "alt": ["5xx spike", "failing requests"],
        "phrases": [
            "the 5xx rate jumped",
            "a growing share of requests failed",
            "error budget burned quickly",
            "HTTP 500 responses surged",
        ],
    },
    "unreachable": {
        "label": "Service unreachable", "group": "Reliability", "alert": "HealthCheckAlert",
        "alt": ["no route to host", "health check failing"],
        "phrases": [
            "health checks stopped passing",
            "the service could not be reached",
            "traffic was not arriving at the pods",
            "synthetic probes reported the endpoint down",
        ],
    },
    "tls_errors": {
        "label": "TLS handshake errors", "group": "Security", "alert": "TlsAlert",
        "alt": ["certificate errors", "handshake failure"],
        "phrases": [
            "TLS handshakes were rejected",
            "clients reported certificate warnings",
            "secure connections failed during negotiation",
            "handshake failure messages filled the logs",
        ],
    },
    "unexpected_behavior": {
        "label": "Unexpected behaviour", "group": "Reliability", "alert": "BehaviourAlert",
        "alt": ["wrong output", "functional regression"],
        "phrases": [
            "the feature behaved differently than designed",
            "customers saw wrong results",
            "a functional regression was reported by QA",
            "responses contained unexpected fields",
        ],
    },
    "startup_failure": {
        "label": "Startup failure", "group": "Reliability", "alert": "CrashLoopAlert",
        "alt": ["crash loop", "container will not start"],
        "phrases": [
            "pods would not start",
            "containers exited right after launch",
            "the service entered a crash loop",
            "readiness probes never succeeded",
        ],
    },
    "auth_failures": {
        "label": "Authentication failures", "group": "Security", "alert": "AuthFailureAlert",
        "alt": ["login failures", "401 responses"],
        "phrases": [
            "logins were rejected",
            "token validation started failing",
            "a wave of 401 responses appeared",
            "service-to-service authentication broke",
        ],
    },
    "throttling": {
        "label": "Throttling", "group": "Performance", "alert": "ThrottleAlert",
        "alt": ["rate limited", "429 responses"],
        "phrases": [
            "clients received 429 responses",
            "requests were being rate limited",
            "throughput plateaued below demand",
            "queues backed up behind limits",
        ],
    },
    "oom_kills": {
        "label": "Out-of-memory kills", "group": "Resources", "alert": "OomKillAlert",
        "alt": ["OOMKilled", "memory kill"],
        "phrases": [
            "containers were OOMKilled",
            "the kernel killed processes for memory",
            "workers vanished with exit code 137",
            "out-of-memory events were logged",
        ],
    },
    "high_memory": {
        "label": "High memory usage", "group": "Resources", "alert": "HighMemoryAlert",
        "alt": ["memory growth", "heap pressure"],
        "phrases": [
            "memory consumption kept growing",
            "heap usage never came back down",
            "resident memory climbed steadily",
            "garbage collection pauses lengthened",
        ],
    },
    "restarts": {
        "label": "Frequent restarts", "group": "Reliability", "alert": "RestartAlert",
        "alt": ["pod restarts", "flapping"],
        "phrases": [
            "pods restarted repeatedly",
            "the restart counter kept climbing",
            "instances flapped in and out of service",
            "workloads were rescheduled over and over",
        ],
    },
    "disk_alerts": {
        "label": "Disk space alerts", "group": "Resources", "alert": "DiskAlert",
        "alt": ["low disk space", "volume nearly full"],
        "phrases": [
            "volumes were almost full",
            "disk usage alarms fired",
            "writes failed for lack of space",
            "free space dropped under the threshold",
        ],
    },
}

CATEGORIES = ["database", "network", "configuration", "capacity", "deployment", "storage"]

# id -> (label, category, symptom keys, runbook id)
ROOT_CAUSES = {
    "rc_conn_pool_exhausted": ("Connection pool exhausted", "database",
                               ["high_latency", "connection_errors", "timeouts"], "rb_db_pool"),
    "rc_slow_query": ("Unindexed slow query", "database",
                      ["high_latency", "high_cpu", "timeouts"], "rb_db_query"),
    "rc_replica_lag": ("Replica lag", "database", ["stale_data", "high_latency"], "rb_db_replica"),
    "rc_deadlock": ("Transaction deadlocks", "database", ["timeouts", "error_rate"], "rb_db_query"),
    "rc_dns_failure": ("DNS resolution failure", "network",
                       ["connection_errors", "error_rate", "unreachable"], "rb_net_dns"),
    "rc_cert_expired": ("Expired TLS certificate", "network",
                        ["tls_errors", "connection_errors"], "rb_net_cert"),
    "rc_lb_misroute": ("Load balancer misrouting", "network",
                       ["error_rate", "unreachable", "high_latency"], "rb_net_lb"),
    "rc_packet_loss": ("Packet loss on network link", "network",
                       ["timeouts", "high_latency", "connection_errors"], "rb_net_lb"),
    "rc_bad_feature_flag": ("Faulty feature flag", "configuration",
                            ["error_rate", "unexpected_behavior"], "rb_cfg_rollback"),
    "rc_wrong_env_var": ("Wrong environment variable", "configuration",
                         ["startup_failure", "error_rate"], "rb_cfg_rollback"),
    "rc_secret_rotation": ("Stale secret after rotation", "configuration",
                           ["auth_failures", "startup_failure"], "rb_cfg_secrets"),
    "rc_quota_misconfig": ("Misconfigured rate limit", "configuration",
                           ["error_rate", "throttling"], "rb_cfg_ratelimit"),
    "rc_memory_leak": ("Memory leak", "capacity",
                       ["oom_kills", "high_memory", "restarts"], "rb_cap_memory"),
    "rc_cpu_saturation": ("CPU saturation", "capacity",
                          ["high_cpu", "high_latency", "timeouts"], "rb_cap_scale"),
    "rc_autoscale_lag": ("Slow autoscaling", "capacity", ["high_latency", "throttling"], "rb_cap_scale"),
    "rc_pod_eviction": ("Node pressure evictions", "capacity",
                        ["restarts", "oom_kills", "unreachable"], "rb_cap_memory"),
    "rc_bad_release": ("Regression in new release", "deployment",
                       ["error_rate", "unexpected_behavior"], "rb_dep_rollback"),
    "rc_migration_failure": ("Failed schema migration", "deployment",
                             ["startup_failure", "error_rate", "stale_data"], "rb_dep_rollback"),
    "rc_image_pull": ("Container image pull failure", "deployment",
                      ["startup_failure", "restarts"], "rb_dep_image"),
    "rc_incompat_api": ("Incompatible API version", "deployment",
                        ["error_rate", "unexpected_behavior"], "rb_dep_rollback"),
    "rc_disk_full": ("Disk full", "storage", ["disk_alerts", "error_rate", "startup_failure"], "rb_sto_disk"),
    "rc_log_flood": ("Log volume flood", "storage", ["disk_alerts", "high_latency"], "rb_sto_disk"),
    "rc_io_throttle": ("Storage IO throttling", "storage",
                       ["high_latency", "timeouts", "throttling"], "rb_sto_io"),
    "rc_backup_stuck": ("Stuck backup job", "storage", ["disk_alerts", "high_cpu"], "rb_sto_io"),
}

RUNBOOKS = {
    "rb_db_pool": "Resize and reset the database connection pool",
    "rb_db_query": "Find and index slow queries, kill blocking transactions",
    "rb_db_replica": "Re-sync lagging database replicas",
    "rb_net_dns": "Flush and fail over DNS resolvers",
    "rb_net_cert": "Renew and redeploy TLS certificates",
    "rb_net_lb": "Drain and rebalance the load balancer pool",
    "rb_cfg_rollback": "Roll back the configuration change",
    "rb_cfg_secrets": "Re-issue and redistribute rotated secrets",
    "rb_cfg_ratelimit": "Adjust rate limit and quota settings",
    "rb_cap_memory": "Capture heap dump, restart and raise memory limits",
    "rb_cap_scale": "Scale out replicas and raise autoscaler targets",
    "rb_dep_rollback": "Roll back to the last known good release",
    "rb_dep_image": "Fix registry credentials and re-pull the image",
    "rb_sto_disk": "Free disk space and expand the volume",
    "rb_sto_io": "Raise provisioned IO or reschedule heavy jobs",
}

ENVIRONMENTS = ["prod-eu", "prod-us", "prod-apac", "staging", "qa-1", "qa-2"]

# (name, tier). The first 7 are platform services with no dependencies.
SERVICE_LIST = [
    ("config-service", "platform"), ("cache-layer", "platform"), ("message-broker", "platform"),
    ("file-storage", "platform"), ("identity-provider", "platform"), ("session-store", "platform"),
    ("audit-log", "platform"),
    ("auth-service", "core"), ("user-profile", "core"), ("catalog-service", "core"),
    ("pricing-service", "core"), ("inventory-service", "core"), ("search-service", "core"),
    ("notification-service", "core"), ("email-gateway", "core"), ("scheduler", "core"),
    ("analytics-pipeline", "core"),
    ("order-service", "edge"), ("payment-service", "edge"), ("billing-service", "edge"),
    ("checkout-service", "edge"), ("recommendation-engine", "edge"), ("report-service", "edge"),
    ("api-gateway", "edge"),
]
N_PLATFORM = 7
