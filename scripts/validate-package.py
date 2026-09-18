#!/usr/bin/env python3
"""Humanizer-ko 패키지 파일을 외부 의존성 없이 검사한다."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read_package_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"{path.relative_to(ROOT)} 파일을 읽을 수 없다: {error}")


SKILL_PATH = ROOT / "SKILL.md"
SKILL = read_package_file(SKILL_PATH)
README = read_package_file(ROOT / "README.md")
try:
    PLUGIN = json.loads(read_package_file(ROOT / ".claude-plugin" / "plugin.json"))
except json.JSONDecodeError as error:
    raise SystemExit(f".claude-plugin/plugin.json의 JSON을 고쳐라: {error}")


def require_match(match: re.Match[str] | None, message: str) -> re.Match[str]:
    if match is None:
        raise SystemExit(message)
    return match


yaml_metadata = require_match(
    re.match(r"\A---\n(.*?)\n---\n", SKILL, re.DOTALL),
    "SKILL.md는 YAML 메타데이터로 시작해야 한다",
).group(1)

for unsupported_field in ("version:", "compatibility:", "allowed-tools:"):
    if re.search(rf"(?m)^{re.escape(unsupported_field)}", yaml_metadata):
        raise SystemExit(f"지원하지 않는 YAML 필드를 지워라: {unsupported_field[:-1]}")

if not re.search(r"(?m)^name:\s*humanizer-ko\s*$", yaml_metadata):
    raise SystemExit("SKILL.md의 name은 humanizer-ko여야 한다")

skill_version = require_match(
    re.search(r'(?m)^\s+version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)["\']?\s*$', yaml_metadata),
    "SKILL.md에 metadata.version을 세 자리 버전으로 넣어라",
).group(1)
readme_version = require_match(
    re.search(r"(?m)^- \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\*", README),
    "README.md에 버전 항목을 넣어라",
).group(1)

package_versions = {skill_version, readme_version, str(PLUGIN.get("version", ""))}
if len(package_versions) != 1:
    raise SystemExit(f"모든 파일의 패키지 버전을 하나로 맞춰라: {sorted(package_versions)}")

skill_files = {path.relative_to(ROOT) for path in ROOT.rglob("SKILL.md")}
if SKILL_PATH.is_symlink() or skill_files != {Path("SKILL.md")}:
    raise SystemExit("저장소 루트에 정규 파일 SKILL.md 하나만 둬라")
if PLUGIN.get("skills") != ["./"]:
    raise SystemExit("Claude 플러그인의 스킬 로더가 저장소 루트를 가리키게 하라")
if PLUGIN.get("name") != "humanizer-ko":
    raise SystemExit("plugin.json의 name은 humanizer-ko여야 한다")

pattern_numbers = [int(number) for number in re.findall(r"(?m)^### ([0-9]+)\. ", SKILL)]
pattern_count = len(pattern_numbers)
if pattern_count == 0 or pattern_numbers != list(range(1, pattern_count + 1)):
    raise SystemExit(f"SKILL.md의 패턴 번호를 1부터 빈틈없이 매겨라: {pattern_numbers}")

readme_numbers = [int(number) for number in re.findall(r"(?m)^\| ([0-9]+) \|", README)]
if sorted(readme_numbers) != pattern_numbers:
    raise SystemExit(
        f"README 표에 패턴 1부터 {pattern_count}까지 한 번씩 나열하라: {sorted(readme_numbers)}"
    )
if f"## {pattern_count}가지 패턴" not in README:
    raise SystemExit(f"README의 패턴 절 제목을 '{pattern_count}가지 패턴'으로 붙여라")

for reference in set(re.findall(r"§([0-9]+)", SKILL + README)):
    if int(reference) > pattern_count:
        raise SystemExit(f"§{reference}는 존재하지 않는 패턴을 가리킨다")

if len(SKILL.splitlines()) > 400:
    raise SystemExit("SKILL.md는 400줄 이하로 유지하라")

print(f"Humanizer-ko 패키지 v{skill_version} 검사 통과")
