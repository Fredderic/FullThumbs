#!/bin/bash
# Auto-increment version and commit script

set -e

echo "🏷️  Auto-version and commit script"

# Get the latest version tag
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "Current version: $LATEST_TAG"

# Extract version numbers (assumes format like v1.2.3)
if echo "$LATEST_TAG" | grep -q "^v[0-9]\+\.[0-9]\+\.[0-9]\+$"; then
    # Parse version numbers
    VERSION_NUM=$(echo "$LATEST_TAG" | sed 's/^v//')
    MAJOR=$(echo "$VERSION_NUM" | cut -d. -f1)
    MINOR=$(echo "$VERSION_NUM" | cut -d. -f2)
    PATCH=$(echo "$VERSION_NUM" | cut -d. -f3)
    
    # Auto-increment patch version
    NEW_PATCH=$((PATCH + 1))
    NEW_TAG="v$MAJOR.$MINOR.$NEW_PATCH"
else
    # No valid version tag found, create initial version
    NEW_TAG="v0.1.0"
fi

echo "New version will be: $NEW_TAG"

# Check if there are staged changes
if ! git diff --cached --quiet; then
    echo "✅ Found staged changes, proceeding with commit..."
    
    # Run tests first
    echo "🧪 Running tests..."
    python run_tests.py
    
    if [ $? -eq 0 ]; then
        echo "✅ All tests passed!"
        
        # Commit the changes
        echo "📝 Committing changes..."
        git commit -m "Update to version $NEW_TAG

$(git diff --cached --name-only | sed 's/^/- /')"
        
        # Create the version tag
        echo "🏷️  Creating version tag: $NEW_TAG"
        git tag "$NEW_TAG"
        
        echo "✅ Successfully committed and tagged version $NEW_TAG"
        echo "💡 To push: git push origin master && git push origin $NEW_TAG"
    else
        echo "❌ Tests failed! Aborting commit."
        exit 1
    fi
else
    echo "❌ No staged changes found. Stage your changes first with 'git add'"
    exit 1
fi
