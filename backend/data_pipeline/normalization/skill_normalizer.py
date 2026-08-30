import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

from backend.data_pipeline.collectors.base_collector import RawDataRecord

logger = logging.getLogger(__name__)


class SkillCategory(str, PyEnum):
    """Standard skill categories."""
    PROGRAMMING = "programming"
    AI_ML = "ai_ml"
    DATA = "data"
    CLOUD = "cloud"
    DEVOPS = "devops"
    SECURITY = "security"
    WEB = "web"
    MOBILE = "mobile"
    DATABASE = "database"
    FRONTEND = "frontend"
    BACKEND = "backend"
    TOOLING = "tooling"
    SOFT_SKILLS = "soft_skills"
    METHODOLOGY = "methodology"
    ARCHITECTURE = "architecture"
    OTHER = "other"


class SkillLevel(str, PyEnum):
    """Proficiency levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class NormalizedSkill:
    """Normalized skill/technology data."""
    name: str
    normalized_name: str
    category: SkillCategory
    description: Optional[str]
    aliases: List[str]
    related_skills: List[str]
    is_technology: bool
    popularity_score: float
    market_demand: Optional[float]
    source: str
    source_url: str
    source_skill_id: str
    quality_score: float
    raw_record: Optional[RawDataRecord] = None


# Comprehensive skill taxonomy
SKILL_TAXONOMY = {
    SkillCategory.PROGRAMMING: [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "julia",
        "perl", "lua", "dart", "elixir", "clojure", "haskell", "f#", "vb.net",
    ],
    SkillCategory.AI_ML: [
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
        "keras", "jax", "hugging face", "transformers", "bert", "gpt", "llama",
        "llm", "rag", "retrieval augmented generation", "fine-tuning", "prompt engineering",
        "computer vision", "nlp", "natural language processing", "reinforcement learning",
        "mlops", "model deployment", "feature store", "experiment tracking",
        "langchain", "llamaindex", "vector database", "embedding", "similarity search",
    ],
    SkillCategory.DATA: [
        "pandas", "numpy", "polars", "dask", "pyspark", "sql", "nosql",
        "data engineering", "etl", "elt", "data pipeline", "data warehouse",
        "data lake", "lakehouse", "airflow", "prefect", "dagster", "dbt",
        "tableau", "power bi", "looker", "metabase", "superset",
        "statistics", "analytics", "visualization", "feature engineering",
    ],
    SkillCategory.CLOUD: [
        "aws", "gcp", "azure", "cloud computing", "serverless", "lambda",
        "cloud functions", "cloud run", "fargate", "ec2", "s3", "rds",
        "dynamodb", "cloudfront", "route53", "vpc", "iam", "cloudformation",
        "terraform", "pulumi", "crossplane", "multi-cloud", "hybrid cloud",
    ],
    SkillCategory.DEVOPS: [
        "docker", "kubernetes", "k8s", "helm", "kustomize", "argocd", "flux",
        "ci/cd", "github actions", "gitlab ci", "jenkins", "circleci", "buildkite",
        "terraform", "ansible", "puppet", "chef", "saltstack",
        "prometheus", "grafana", "datadog", "new relic", "elastic stack",
        "observability", "monitoring", "logging", "tracing", "alerting",
        "gitops", "infrastructure as code", "iac", "platform engineering",
    ],
    SkillCategory.SECURITY: [
        "security", "cybersecurity", "application security", "network security",
        "cloud security", "zero trust", "oauth", "oidc", "saml", "jwt",
        "penetration testing", "vulnerability assessment", "compliance",
        "soc 2", "iso 27001", "gdpr", "hipaa", "pci dss",
        "cryptography", "encryption", "tls", "mtls", "spiffe", "spire",
    ],
    SkillCategory.WEB: [
        "html", "css", "sass", "less", "tailwind", "bootstrap", "material ui",
        "react", "vue", "angular", "svelte", "next.js", "nuxt", "remix",
        "astro", "qwik", "solid", "htmx", "alpine.js",
        "webpack", "vite", "rollup", "esbuild", "turbopack",
        "typescript", "eslint", "prettier", "jest", "vitest", "cypress", "playwright",
        "web accessibility", "wcag", "seo", "core web vitals",
    ],
    SkillCategory.MOBILE: [
        "ios", "android", "swift", "kotlin", "flutter", "react native",
        "xamarin", "ionic", "capacitor", "expo", "swiftui", "jetpack compose",
        "mobile development", "app store", "play store", "push notifications",
    ],
    SkillCategory.DATABASE: [
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
        "dynamodb", "cassandra", "couchbase", "neo4j", "influxdb", "timescaledb",
        "cockroachdb", "planetscale", "supabase", "firebase", "supabase",
        "orm", "prisma", "sqlalchemy", "django orm", "entity framework",
        "database design", "indexing", "query optimization", "sharding",
        "replication", "backup", "migration",
    ],
    SkillCategory.FRONTEND: [
        "react", "vue", "angular", "svelte", "next.js", "nuxt", "remix",
        "state management", "redux", "zustand", "jotai", "recoil", "mobx",
        "component library", "storybook", "design system", "css-in-js",
        "styled-components", "emotion", "tailwind", "scss", "css modules",
        "testing", "jest", "vitest", "react testing library", "cypress", "playwright",
    ],
    SkillCategory.BACKEND: [
        "api design", "rest", "graphql", "grpc", "websockets", "server-sent events",
        "microservices", "monolith", "modular monolith", "domain driven design",
        "clean architecture", "hexagonal architecture", "event sourcing", "cqrs",
        "message queue", "kafka", "rabbitmq", "nats", "redis streams",
        "caching", "redis", "memcached", "cdn", "rate limiting", "circuit breaker",
        "authentication", "authorization", "rbac", "abac", "oauth2", "openid connect",
    ],
    SkillCategory.TOOLING: [
        "git", "github", "gitlab", "bitbucket", "svn",
        "vscode", "intellij", "vim", "neovim", "emacs", "cursor",
        "docker", "podman", "buildah", "skaffold", "telepresence",
        "linux", "bash", "zsh", "fish", "tmux", "ssh", "vpn",
        "package manager", "npm", "yarn", "pnpm", "cargo", "go modules", "maven", "gradle",
    ],
    SkillCategory.SOFT_SKILLS: [
        "communication", "leadership", "teamwork", "problem solving",
        "critical thinking", "adaptability", "time management", "mentoring",
        "code review", "technical writing", "presentation", "negotiation",
        "conflict resolution", "empathy", "collaboration",
    ],
    SkillCategory.METHODOLOGY: [
        "agile", "scrum", "kanban", "xp", "lean", "waterfall",
        "tdd", "bdd", "ddd", "clean code", "solid principles",
        "design patterns", "refactoring", "legacy code", "technical debt",
        "continuous integration", "continuous deployment", "continuous delivery",
    ],
    SkillCategory.ARCHITECTURE: [
        "system design", "distributed systems", "scalability", "availability",
        "consistency", "partition tolerance", "cap theorem", "paxos", "raft",
        "service mesh", "istio", "linkerd", "consul", "api gateway",
        "event driven architecture", "event sourcing", "cqrs", "saga pattern",
        "serverless architecture", "edge computing", "multi-region",
    ],
}

# Aliases for common skill variations
SKILL_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes",
    "tf": "terraform",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "rl": "reinforcement learning",
    "ci": "ci/cd",
    "cd": "ci/cd",
    "iac": "infrastructure as code",
    "db": "database",
    "api": "api design",
    "ui": "frontend",
    "ux": "frontend",
    "be": "backend",
    "fe": "frontend",
    "devops": "devops",
    "mlops": "mlops",
    "llmops": "mlops",
}


def classify_skill_category(skill: str) -> SkillCategory:
    """Classify a skill into a category."""
    skill_lower = skill.lower().strip()
    
    for category, skills in SKILL_TAXONOMY.items():
        if skill_lower in [s.lower() for s in skills]:
            return category
        
        # Check partial matches
        for s in skills:
            if s in skill_lower or skill_lower in s:
                return category
    
    return SkillCategory.OTHER


def normalize_skill_name(skill: str) -> str:
    """Normalize skill name to standard form."""
    skill_lower = skill.lower().strip()
    
    # Check aliases
    if skill_lower in SKILL_ALIASES:
        return SKILL_ALIASES[skill_lower]
    
    # Check taxonomy for exact match
    for category, skills in SKILL_TAXONOMY.items():
        for s in skills:
            if s.lower() == skill_lower:
                return s
    
    # Return title case for unknown skills
    return skill.title()


def extract_related_skills(skill: str) -> List[str]:
    """Extract related skills from the same category."""
    category = classify_skill_category(skill)
    if category == SkillCategory.OTHER:
        return []
    
    skills = SKILL_TAXONOMY.get(category, [])
    # Return up to 5 related skills from same category
    return [s for s in skills if s.lower() != skill.lower()][:5]


class SkillNormalizer:
    """Normalize skill/technology data from various sources."""

    def __init__(self):
        self.name = "skill_normalizer"

    def normalize(self, raw_record: RawDataRecord) -> NormalizedSkill:
        """Normalize a single raw skill record."""
        payload = raw_record.raw_payload
        logger.debug(f"Normalizing skill: {payload.get('name')}")

        name = payload.get("name", "").strip()
        normalized_name = normalize_skill_name(name)
        category = payload.get("category")
        
        if isinstance(category, str):
            try:
                category = SkillCategory(category.lower())
            except ValueError:
                category = classify_skill_category(normalized_name)
        else:
            category = classify_skill_category(normalized_name)
        
        description = payload.get("description", "").strip() if payload.get("description") else None
        
        # Extract aliases from payload or generate
        aliases = payload.get("aliases") or []
        if name.lower() != normalized_name.lower():
            aliases.append(name)
        
        related_skills = payload.get("related_skills") or extract_related_skills(normalized_name)
        
        is_technology = payload.get("is_technology", category in [
            SkillCategory.PROGRAMMING, SkillCategory.AI_ML, SkillCategory.DATA,
            SkillCategory.CLOUD, SkillCategory.DEVOPS, SkillCategory.DATABASE,
            SkillCategory.WEB, SkillCategory.MOBILE, SkillCategory.FRONTEND,
            SkillCategory.BACKEND, SkillCategory.TOOLING,
        ])
        
        popularity_score = payload.get("popularity_score", 0.5)
        if isinstance(popularity_score, str):
            try:
                popularity_score = float(popularity_score)
            except Exception:
                popularity_score = 0.5
        
        market_demand = payload.get("market_demand")
        if isinstance(market_demand, str):
            try:
                market_demand = float(market_demand)
            except Exception:
                market_demand = None

        return NormalizedSkill(
            name=name,
            normalized_name=normalized_name,
            category=category,
            description=description,
            aliases=list(set(aliases)),
            related_skills=related_skills,
            is_technology=is_technology,
            popularity_score=popularity_score,
            market_demand=market_demand,
            source=raw_record.source_name,
            source_url=payload.get("source_url", ""),
            source_skill_id=payload.get("source_skill_id", raw_record.external_id),
            quality_score=payload.get("quality_score", 0.0),
            raw_record=raw_record,
        )

    def normalize_batch(self, raw_records: List[RawDataRecord]) -> List[NormalizedSkill]:
        """Normalize multiple raw skill records."""
        return [self.normalize(record) for record in raw_records]