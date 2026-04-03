#!/bin/bash
set -e

# Auto-bump version based on conventional commits since last tag.
# Updates pyproject.toml, CHANGELOG.md, commits, and tags.
# Usage: ./bump-version.sh [--dry-run]

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# Get latest tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -z "$LAST_TAG" ]]; then
    echo "No existing tags found. Tag as v1.0.0? (y/n)"
    read -r ans
    [[ "$ans" == "y" ]] && git tag v1.0.0 && echo "Tagged v1.0.0"
    exit 0
fi

echo "Last tag: $LAST_TAG"

# Parse current version (strip leading 'v')
VERSION="${LAST_TAG#v}"
IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"

# If the tag is just a single number (e.g. v1), normalize to semver format
if [[ -z "$MINOR" ]]; then MINOR=0; fi
if [[ -z "$PATCH" ]]; then PATCH=0; fi

# Analyze commits since last tag
COMMITS=$(git log "${LAST_TAG}..HEAD" --pretty=format:"%s")

if [[ -z "$COMMITS" ]]; then
    echo "No new commits since $LAST_TAG."
    exit 0
fi

echo ""
echo "Commits since $LAST_TAG:"
echo "$COMMITS" | sed 's/^/  /'
echo ""

# Determine bump level
BUMP="patch"
while IFS= read -r msg; do
    if echo "$msg" | grep -qiE '^feat(\(.+\))?!:|BREAKING CHANGE'; then
        BUMP="major"
        break
    elif echo "$msg" | grep -qiE '^feat(\(.+\))?:'; then
        BUMP="minor"
    fi
done <<< "$COMMITS"

# Calculate new version
case "$BUMP" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_TAG="v${MAJOR}.${MINOR}.${PATCH}"
NEW_VER="${MAJOR}.${MINOR}.${PATCH}"
echo "Bump: $BUMP → $NEW_TAG"

if $DRY_RUN; then
    echo "(dry run, not tagging)"
    exit 0
fi

echo "Create tag $NEW_TAG? (y/n)"
read -r ans
if [[ "$ans" != "y" ]]; then
    echo "Aborted."
    exit 0
fi

# ---------------------------------------------------------------
# Generate CHANGELOG entry from conventional commits
# ---------------------------------------------------------------
TODAY=$(date +%Y-%m-%d)

# Categorize commits
ADDED=""
CHANGED=""
FIXED=""
OTHER=""

while IFS= read -r msg; do
    # Strip type prefix to get description
    desc=$(echo "$msg" | sed -E 's/^[a-z]+(\(.+\))?!?:\s*//')
    # Capitalize first letter
    desc="$(echo "${desc:0:1}" | tr '[:lower:]' '[:upper:]')${desc:1}"

    case "$msg" in
        feat!:*|feat\(*\)!:*)  ADDED="${ADDED}- ${desc}\n" ;;
        feat:*|feat\(*\):*)    ADDED="${ADDED}- ${desc}\n" ;;
        fix:*|fix\(*\):*)      FIXED="${FIXED}- ${desc}\n" ;;
        docs:*|docs\(*\):*)    CHANGED="${CHANGED}- ${desc}\n" ;;
        refactor:*|refactor\(*\):*) CHANGED="${CHANGED}- ${desc}\n" ;;
        chore:*bump*|chore:*version*) ;; # skip version bump commits
        chore:*|chore\(*\):*)  OTHER="${OTHER}- ${desc}\n" ;;
        *)                     OTHER="${OTHER}- ${desc}\n" ;;
    esac
done <<< "$COMMITS"

# Build the entry
ENTRY="## [${NEW_VER}] - ${TODAY}\n"

if [[ -n "$ADDED" ]]; then
    ENTRY="${ENTRY}\n### Added\n\n${ADDED}"
fi
if [[ -n "$CHANGED" ]]; then
    ENTRY="${ENTRY}\n### Changed\n\n${CHANGED}"
fi
if [[ -n "$FIXED" ]]; then
    ENTRY="${ENTRY}\n### Fixed\n\n${FIXED}"
fi
if [[ -n "$OTHER" ]]; then
    ENTRY="${ENTRY}\n### Other\n\n${OTHER}"
fi

# Insert entry after the header (line 5) in CHANGELOG.md
if [[ -f CHANGELOG.md ]]; then
    # Find the line number of the first "## [" (first version entry)
    FIRST_VER_LINE=$(grep -n '^## \[' CHANGELOG.md | head -1 | cut -d: -f1)
    if [[ -n "$FIRST_VER_LINE" ]]; then
        {
            head -n $((FIRST_VER_LINE - 1)) CHANGELOG.md
            echo ""
            printf "%b" "$ENTRY"
            tail -n +"$FIRST_VER_LINE" CHANGELOG.md
        } > CHANGELOG.md.tmp
    else
        {
            cat CHANGELOG.md
            echo ""
            printf "%b" "$ENTRY"
        } > CHANGELOG.md.tmp
    fi
    mv CHANGELOG.md.tmp CHANGELOG.md
else
    {
        echo "# Changelog"
        echo ""
        echo "All notable changes to this project will be documented in this file."
        echo ""
        echo "Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [Semantic Versioning](https://semver.org/)."
        echo ""
        printf "%b" "$ENTRY"
    } > CHANGELOG.md
fi

echo ""
echo "--- CHANGELOG entry ---"
printf "%b" "$ENTRY"
echo "-----------------------"

# Update pyproject.toml + commit + tag
sed -i '' "s/^version = \".*\"/version = \"${NEW_VER}\"/" pyproject.toml
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to ${NEW_TAG}"
git tag "$NEW_TAG"
echo ""
echo "Updated pyproject.toml, CHANGELOG.md, and tagged $NEW_TAG"
